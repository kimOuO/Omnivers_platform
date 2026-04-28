"""RAN Labels Extension — 2D HUD overlay.

Labels are `omni.ui` widgets (NOT `omni.ui.scene`) on a transparent overlay
on top of the viewport. Every tick we:
  1. Read UE/gNB world position from USD.
  2. Project world → pixel via the active viewport's view × projection matrix.
  3. Update `Placer.offset_x / offset_y` and `Label.text` — these setters
     actually trigger repaint in `omni.ui` (unlike `omni.ui.scene`).

No USD label prims, no DynamicTextureProvider. Simple 2D HUD.
"""
from __future__ import annotations

import math

import omni.ext
import omni.kit.app
import omni.usd
import omni.ui as ui
from pxr import Gf, Tf, Usd, UsdGeom


# --- Config -----------------------------------------------------------------

UE_OFFSET_Y = 75.0
GNB_OFFSET_Y = 8.0
UPDATE_HZ = 120.0  # ceiling — actual work is gated by _data_dirty / camera_moved

# 0xAABBGGRR (omni.ui convention)
WHITE = 0xFFFFFFFF
BLACK = 0xFF000000
GOOD = 0xFF50AF4C
MID = 0xFF0098FF
BAD = 0xFF3539E5
BG_DARK = 0xA0000000   # semi-transparent black (UE: white text)
BG_LIGHT = 0xC0FFFFFF  # semi-transparent white (gNB: black text)


def _rsrp_color(v):
    if v is None:
        return BLACK
    if v > -80:
        return GOOD
    if v > -100:
        return MID
    return BAD


def _rsrp_text(v):
    return f"RSRP {v:.1f} dBm" if v is not None else "RSRP -"


def _sinr_text(v):
    return f"SINR {v:.1f} dB" if v is not None else "SINR -"


def _gnb_fp(freq, power):
    f = f"{freq:.1f}GHz" if freq is not None else "?GHz"
    p = f"{power:.0f}dBm" if power is not None else "?dBm"
    return f"{f} / {p}"


def _get_gnb_cfg():
    try:
        from mitlab.ran.scene.builder.extension import RANSceneBuilderExtension, _to_prim_name
        b = RANSceneBuilderExtension._instance
        if b and b._config:
            result = {}
            for g in (b._config.get("gnbs") or []):
                result[g["name"]] = g
                result[_to_prim_name(g["name"])] = g
            return result
    except Exception:  # noqa: BLE001
        pass
    return {}


def _read_signal(prim):
    out = {"serving_cell": None, "rsrp_dbm": None, "sinr_db": None}
    a = prim.GetAttribute("ran:serving_cell")
    if a and a.HasValue():
        out["serving_cell"] = str(a.Get())
    a = prim.GetAttribute("ran:rsrp_dbm")
    if a and a.HasValue():
        out["rsrp_dbm"] = float(a.Get())
    a = prim.GetAttribute("ran:sinr_db")
    if a and a.HasValue():
        out["sinr_db"] = float(a.Get())
    return out


def _get_world_pos(prim):
    xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    t = xf.ExtractTranslation()
    return float(t[0]), float(t[1]), float(t[2])


def _first_attr(obj, *names):
    """Return first non-None attribute by name, else None."""
    for n in names:
        if hasattr(obj, n):
            try:
                v = getattr(obj, n)
            except Exception:  # noqa: BLE001
                continue
            if v is not None:
                return v
    return None


def _to_gf_matrix(m):
    """Best-effort convert anything to Gf.Matrix4d."""
    if m is None:
        return None
    if isinstance(m, Gf.Matrix4d):
        return m
    try:
        return Gf.Matrix4d(m)
    except Exception:  # noqa: BLE001
        pass
    # Try flattening numpy / list-of-lists
    try:
        flat = [float(x) for row in m for x in row]
        if len(flat) == 16:
            return Gf.Matrix4d(*flat)
    except Exception:  # noqa: BLE001
        pass
    try:
        flat = [float(x) for x in m]
        if len(flat) == 16:
            return Gf.Matrix4d(*flat)
    except Exception:  # noqa: BLE001
        pass
    return None


# --- Per-label widget -------------------------------------------------------


class _LabelWidget:
    """One label = Placer + VStack of rows. Lives on the overlay ZStack."""

    def __init__(self, container, is_ue: bool):
        self.is_ue = is_ue
        n_rows = 4 if is_ue else 5   # gNB now carries 5 rows: name, freq/power, BW, PCI, cell
        bg = BG_DARK if is_ue else BG_LIGHT
        with container:
            self.placer = ui.Placer(offset_x=0, offset_y=0, draggable=False)
            with self.placer:
                self.stack = ui.VStack(
                    width=0,
                    height=0,
                    spacing=0,
                    style={"background_color": bg, "padding": 4, "border_radius": 3},
                )
                with self.stack:
                    self.rows = [
                        ui.Label("", alignment=ui.Alignment.CENTER, height=0)
                        for _ in range(n_rows)
                    ]
        self._visible = True
        self._last_key = ""

    def set_visible(self, visible: bool) -> None:
        if visible == self._visible:
            return
        self._visible = visible
        try:
            self.placer.visible = visible
        except Exception:  # noqa: BLE001
            pass

    def set_pos(self, px: float, py: float) -> None:
        try:
            self.placer.offset_x = px
            self.placer.offset_y = py
        except Exception:  # noqa: BLE001
            pass

    def set_rows(self, rows: list, key: str) -> None:
        """rows = [(text, color, font_size), ...]"""
        if key == self._last_key:
            return
        for i, (text, color, size) in enumerate(rows):
            if i >= len(self.rows):
                break
            lbl = self.rows[i]
            try:
                lbl.text = text
                lbl.style = {
                    "color": color,
                    "font_size": size,
                    "margin": 0,
                    "background_color": 0x00000000,
                }
            except Exception:  # noqa: BLE001
                pass
        self._last_key = key

    def destroy(self) -> None:
        try:
            self.placer.visible = False
        except Exception:  # noqa: BLE001
            pass


# --- Extension --------------------------------------------------------------


class RANLabelsExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        print(f"[mitlab.ran.labels] startup ({ext_id}) — HUD mode (event-driven)")
        self._frame = None
        self._root_stack: ui.ZStack | None = None
        self._labels: dict[str, _LabelWidget] = {}
        self._throttle: float = 0.0
        self._tick_count: int = 0
        self._vp_err_printed = False

        # Event-driven refresh:
        #   - USD Tf.Notice marks _data_dirty when any UE/gNB prim changes
        #     (attr write, xform write, add/remove).
        #   - Per-frame tick short-circuits unless _data_dirty OR camera moved.
        #   - On idle (no POST, no animation, no camera drag) tick does nothing.
        self._data_dirty: bool = True           # start dirty so first paint works
        self._last_mvp: Gf.Matrix4d | None = None
        self._usd_notice = None

        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="ran.labels.hud"
        )

    def on_shutdown(self) -> None:
        self._update_sub = None
        if self._usd_notice is not None:
            try:
                self._usd_notice.Revoke()
            except Exception:  # noqa: BLE001
                pass
            self._usd_notice = None
        for lbl in list(self._labels.values()):
            try:
                lbl.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._labels.clear()
        self._frame = None
        self._root_stack = None
        print("[mitlab.ran.labels] shutdown")

    # ---- USD notice subscription ----------------------------------------

    def _ensure_usd_subscription(self) -> None:
        if self._usd_notice is not None:
            return
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        try:
            self._usd_notice = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged, self._on_usd_changed, stage
            )
            print("[mitlab.ran.labels] USD notice registered (event-driven)")
        except Exception as e:  # noqa: BLE001
            print(f"[mitlab.ran.labels] Tf.Notice.Register failed: {e}")

    def _on_usd_changed(self, notice, sender) -> None:
        """Fires synchronously on any USD write. Mark dirty if a UE/gNB changed.
        Kept cheap — just flips a bool. Real work happens on next frame tick."""
        try:
            for p in notice.GetResyncedPaths():
                nm = p.GetPrimPath().name
                if nm.startswith("UE") or nm.startswith("gNB"):
                    self._data_dirty = True
                    return
            for p in notice.GetChangedInfoOnlyPaths():
                nm = p.GetPrimPath().name
                if nm.startswith("UE") or nm.startswith("gNB"):
                    self._data_dirty = True
                    return
        except Exception:  # noqa: BLE001
            self._data_dirty = True

    # ---- overlay attach --------------------------------------------------

    def _ensure_overlay(self) -> bool:
        if self._frame is not None and self._root_stack is not None:
            return True
        try:
            import omni.kit.viewport.utility as vp_utils
        except ImportError:
            return False
        vp_window = vp_utils.get_active_viewport_window()
        if vp_window is None:
            if self._tick_count < 3:
                print("[mitlab.ran.labels] no active viewport window yet")
            return False
        try:
            frame = vp_window.get_frame("mitlab.ran.labels.hud")
        except Exception as e:  # noqa: BLE001
            print(f"[mitlab.ran.labels] get_frame failed: {e}")
            return False
        try:
            with frame:
                # Fill the viewport frame so Placer offsets are in viewport pixels.
                self._root_stack = ui.ZStack(
                    width=ui.Percent(100), height=ui.Percent(100)
                )
            self._frame = frame
            print(f"[mitlab.ran.labels] HUD overlay attached (frame={frame})")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[mitlab.ran.labels] build ZStack failed: {e}")
            self._frame = None
            self._root_stack = None
            return False

    # ---- world-to-pixel projection ---------------------------------------

    def _get_viewport_context(self):
        """Return (mvp_matrix, width_px, height_px) or None.

        Kit exposes view/proj matrices and resolution under different attribute
        names across SDK versions — try a few, and on first tick dump the
        viewport_api surface so we can see what this build actually has.
        """
        try:
            import omni.kit.viewport.utility as vp_utils
            vp = vp_utils.get_active_viewport()
            if vp is None:
                if self._tick_count < 3:
                    print("[mitlab.ran.labels] get_active_viewport() returned None")
                return None

            # One-shot introspection
            if self._tick_count == 1:
                attrs = [a for a in dir(vp) if not a.startswith("_")]
                print(f"[mitlab.ran.labels] viewport_api type={type(vp).__name__}")
                print(f"[mitlab.ran.labels] viewport_api attrs: {attrs}")

            view = _first_attr(vp, "view_matrix", "view", "world_to_view")
            proj = _first_attr(vp, "projection_matrix", "projection", "view_to_ndc")
            if view is None or proj is None:
                if not self._vp_err_printed:
                    print(f"[mitlab.ran.labels] view={view!r} proj={proj!r} — matrix attrs missing")
                    self._vp_err_printed = True
                return None

            view = _to_gf_matrix(view)
            proj = _to_gf_matrix(proj)
            if view is None or proj is None:
                if not self._vp_err_printed:
                    print("[mitlab.ran.labels] matrix conversion to Gf.Matrix4d failed")
                    self._vp_err_printed = True
                return None

            mvp = view * proj

            # Resolution: try a few attribute conventions
            res = _first_attr(vp, "resolution")
            w = h = None
            if res is not None:
                try:
                    w, h = float(res[0]), float(res[1])
                except Exception:  # noqa: BLE001
                    w = h = None
            if (w is None or h is None) and hasattr(vp, "full_viewport_frame"):
                fr = vp.full_viewport_frame
                try:
                    w, h = float(fr[2]), float(fr[3])
                except Exception:  # noqa: BLE001
                    pass
            if w is None or h is None:
                if not self._vp_err_printed:
                    print("[mitlab.ran.labels] cannot determine viewport resolution")
                    self._vp_err_printed = True
                return None

            if w <= 0 or h <= 0:
                return None
            return mvp, w, h
        except Exception as e:  # noqa: BLE001
            if not self._vp_err_printed:
                print(f"[mitlab.ran.labels] viewport api error: {e}")
                import traceback
                traceback.print_exc()
                self._vp_err_printed = True
            return None

    @staticmethod
    def _project(world_pos, mvp, width, height):
        """World Gf.Vec3d → (px, py, visible)."""
        try:
            ndc = mvp.Transform(world_pos)  # auto-divides by w
        except Exception:  # noqa: BLE001
            return 0.0, 0.0, False
        # Off-screen / behind camera filter
        nx, ny, nz = float(ndc[0]), float(ndc[1]), float(ndc[2])
        if nz < -1.0 or nz > 1.0:
            return 0.0, 0.0, False
        if nx < -1.5 or nx > 1.5 or ny < -1.5 or ny > 1.5:
            return 0.0, 0.0, False
        px = (nx * 0.5 + 0.5) * width
        py = (1.0 - (ny * 0.5 + 0.5)) * height
        return px, py, True

    # ---- tick ------------------------------------------------------------

    def _on_update(self, event) -> None:
        self._ensure_usd_subscription()
        if not self._ensure_overlay():
            return

        dt = float(event.payload.get("dt", 0.0))
        self._throttle += dt
        if self._throttle < 1.0 / UPDATE_HZ:
            return
        self._throttle = 0.0
        self._tick_count += 1

        ctx = self._get_viewport_context()
        if ctx is None:
            return
        mvp, width, height = ctx

        # Event-driven short-circuit: if neither data nor camera changed, skip.
        # Camera movement is detected by matrix diff (user drag / orbit writes
        # camera prim xformOps — which ALSO fire the USD notice, but that would
        # mark us data_dirty; matrix compare is defense-in-depth / catches cases
        # where camera isn't the active prim we subscribed to).
        camera_moved = self._last_mvp is None or mvp != self._last_mvp
        if not (self._data_dirty or camera_moved):
            return
        self._last_mvp = Gf.Matrix4d(mvp)
        self._data_dirty = False

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        world = stage.GetPrimAtPath("/World")
        if not world.IsValid():
            return

        gnb_cfg = _get_gnb_cfg()
        seen = set()

        for child in world.GetChildren():
            name = child.GetName()
            # Skip special prims
            if name in ("Ground", "Environment", "SunLight"):
                continue

            child_names = {c.GetName() for c in child.GetChildren()}

            # Determine type: gNB has Tower
            if "Tower" in child_names:
                is_ue = False
            # UE: has ran:rsrp_dbm or Body/Head children
            elif child.HasAttribute("ran:rsrp_dbm") or "Body" in child_names:
                is_ue = True
            # UE fallback: if it has children and is not a building (no 'Asset' child)
            elif len(child_names) > 0 and "Asset" not in child_names:
                is_ue = True
            else:
                continue

            seen.add(name)
            self._update_one(child, name, is_ue, gnb_cfg, mvp, width, height)

        # hide stale
        for key in list(self._labels.keys()):
            if key not in seen:
                self._labels[key].set_visible(False)

        if self._tick_count in (1, 5, 30) or self._tick_count % 300 == 0:
            # On first tick: log one sample projection so we can see if numbers
            # are sensible (px/py should be within 0..width/height).
            sample = ""
            for k, lbl in list(self._labels.items())[:2]:
                sample += f" {k}=({lbl.placer.offset_x},{lbl.placer.offset_y})"
            print(
                f"[mitlab.ran.labels] tick #{self._tick_count}: "
                f"labels={len(self._labels)} vp={int(width)}x{int(height)} seen={len(seen)}{sample}"
            )

    def _update_one(self, prim, name, is_ue, gnb_cfg, mvp, width, height):
        if is_ue:
            # UE: container has proper translate (animation writes here).
            x, y, z = _get_world_pos(prim)
            offset = UE_OFFSET_Y
        else:
            # gNB: scene.builder creates /World/gNB_xxx as an empty Xform and
            # puts the translate on children (Tower/Antenna). Reading the
            # container's xform returns (0,0,0) — use config position instead.
            cfg = gnb_cfg.get(name) or {}
            pos = cfg.get("position") or [0.0, 0.0, 0.0]
            scale = float(cfg.get("scale") or 1.0)
            x = float(pos[0])
            z = float(pos[2])
            # gNB "height" in scene.builder = config.position[1] * scale;
            # antenna sits at top. Put label a bit above the antenna sphere.
            tower_height = float(pos[1]) * scale
            ant_radius = 6.0 * scale
            y = tower_height + 2 * ant_radius
            offset = GNB_OFFSET_Y
        world_pos = Gf.Vec3d(x, y + offset, z)
        px, py, visible = self._project(world_pos, mvp, width, height)

        lbl = self._labels.get(name)
        if lbl is None:
            lbl = _LabelWidget(self._root_stack, is_ue)
            self._labels[name] = lbl
            print(f"[mitlab.ran.labels] ✓ created HUD label for {name} (world={x:.1f},{y:.1f},{z:.1f} → px={px:.0f},{py:.0f} vis={visible})")

        if not visible:
            lbl.set_visible(False)
            return
        lbl.set_visible(True)
        lbl.set_pos(px, py)

        if is_ue:
            sig = _read_signal(prim)
            rows = [
                (name, BLACK, 24),
                (sig["serving_cell"] or "-", BLACK, 18),
                (_rsrp_text(sig["rsrp_dbm"]), _rsrp_color(sig["rsrp_dbm"]), 18),
                (_sinr_text(sig["sinr_db"]), BLACK, 18),
            ]
            key = f"{name}|{sig['serving_cell']}|{sig['rsrp_dbm']}|{sig['sinr_db']}"
        else:
            cfg = gnb_cfg.get(name, {})
            freq = cfg.get("frequency_ghz") or (cfg.get("freq_mhz", 0) / 1000.0 if cfg.get("freq_mhz") else None)
            power = cfg.get("power_dbm")
            bw = cfg.get("bandwidth_mhz") or (cfg.get("bw_hz", 0) / 1e6 if cfg.get("bw_hz") else None)
            pci = cfg.get("pci")
            cell_id = cfg.get("cell_id")
            rows = [
                (name, BLACK, 24),
                (_gnb_fp(freq, power), BLACK, 18),
                (f"BW {bw:.0f}MHz" if bw is not None else "BW ?", BLACK, 18),
                (f"PCI {pci}" if pci is not None else "PCI -", BLACK, 18),
                (f"Cell {cell_id}" if cell_id is not None else "Cell -", BLACK, 18),
            ]
            key = f"{name}|{freq}|{power}|{bw}|{pci}|{cell_id}"

        lbl.set_rows(rows, key)
