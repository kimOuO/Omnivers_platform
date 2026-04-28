import omni.ext
import omni.ui as ui
import omni.usd
import omni.kit.commands
from pxr import Usd, UsdGeom, Gf, Sdf, Vt
import json
import os
import math
import re
import time


def _to_prim_name(name: str) -> str:
    """Sanitize a string to a valid USD prim identifier (must start with letter/underscore)."""
    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', str(name))
    if sanitized and sanitized[0].isdigit():
        sanitized = f'_{sanitized}'
    return sanitized or '_unnamed'


# Default ground configuration — used in all scenes
DEFAULT_GROUND_CONFIG = {
    "material": "grass",
    "size": [1000, 1000]
}


class RANSceneBuilderExtension(omni.ext.IExt):

    _instance = None

    def on_startup(self, ext_id):
        RANSceneBuilderExtension._instance = self
        print(f"[mitlab.ran.scene.builder] Extension startup ({__file__})")

        self._config = None
        self._animated_ues = []
        self._animation_sub = None
        self._animating = False

        self._window = ui.Window("RAN Scene Builder", width=300, height=300)
        with self._window.frame:
            with ui.VStack(spacing=8):
                ui.Label("RAN Scene Builder", alignment=ui.Alignment.CENTER, height=30)
                ui.Button("Build Scene", clicked_fn=self._build_scene, height=40)
                ui.Button("Clear Scene", clicked_fn=self._clear_scene, height=40)
                ui.Spacer(height=4)
                ui.Button("\u25b6 Start Animation", clicked_fn=self._start_animation, height=40)
                ui.Button("\u25a0 Stop Animation", clicked_fn=self._stop_animation, height=40)
                self._status = ui.Label("Ready", alignment=ui.Alignment.CENTER, height=20)

    def on_shutdown(self):
        RANSceneBuilderExtension._instance = None
        self._stop_animation()
        self._animated_ues = []
        print("[mitlab.ran.scene.builder] Extension shutdown")

    def _load_config(self):
        # Priority: Dynamic API (DB-driven) > runtime_config file > env var > legacy files
        # 1. Try dynamic API first (always fetch fresh from DB)
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        try:
            import urllib.request
            import json as json_lib
            api_url = f"{backend_url}/api/v0.1/RAN/Scene/SceneLayoutReader/read"
            print(f"[RAN] Loading config from API: {api_url}")
            with urllib.request.urlopen(api_url, timeout=5) as response:
                data = json_lib.loads(response.read().decode())
                if data.get("success"):
                    config = data.get("data", {})
                    print(f"[RAN] Config loaded from API: {len(config.get('buildings', []))} buildings")
                    return config
        except Exception as e:
            print(f"[RAN] API load failed (non-blocking): {e}")

        # 2. Fallback to static files
        candidates = []

        # Home runtime config (from API POST /scene/config)
        home_runtime = os.path.expanduser("~/.omniverse_runtime_config.json")
        candidates.append(("home runtime", home_runtime))

        # /tmp runtime config (fallback if home write fails)
        tmp_runtime = "/tmp/.omniverse_runtime_config.json"
        candidates.append(("/tmp runtime", tmp_runtime))

        # RAN_SCENE_CONFIG env var
        env_path = os.environ.get("RAN_SCENE_CONFIG")
        if env_path:
            candidates.append(("env RAN_SCENE_CONFIG", os.path.expanduser(env_path)))

        # Legacy paths
        candidates.append(("legacy ~/omniverse", os.path.expanduser("~/omniverse/scene_config.json")))
        candidates.append(("legacy old static", os.path.expanduser("~/XAPP_DT/Omnivers_platform/scene_config.json")))

        # Try each candidate in order
        for name, path in candidates:
            if os.path.exists(path):
                print(f"[RAN] Loading config from {name}: {path}")
                try:
                    with open(path, "r") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"[RAN] Failed to load from {name}: {e}")
                    continue

        # No config found - return empty scene
        print("[RAN] No scene config found at any candidate paths")
        raise RuntimeError("No scene config file found")

    def _as_abs_path(self, path_value):
        if not path_value:
            return None
        path_value = os.path.expanduser(str(path_value))
        if os.path.isabs(path_value):
            return path_value
        return os.path.abspath(path_value)

    def _ensure_xform(self, stage, prim_path):
        if stage.GetPrimAtPath(prim_path).IsValid():
            return stage.GetPrimAtPath(prim_path)
        return UsdGeom.Xform.Define(stage, prim_path).GetPrim()

    def _add_reference(self, stage, prim_path, asset_path):
        asset_path = self._as_abs_path(asset_path)
        if not asset_path or not os.path.exists(asset_path):
            print(f"[RAN] Reference skipped (missing): {asset_path}")
            return None

        prim = self._ensure_xform(stage, prim_path)
        prim.GetReferences().ClearReferences()

        # Simple approach: just add the reference to the entire asset
        # USD will handle composition correctly
        prim.GetReferences().AddReference(asset_path)

        # Some assets use payloads; force-load so geometry appears.
        try:
            prim.Load()
        except Exception:
            pass
        print(f"[RAN] Referenced: {asset_path} -> {prim_path}")
        return prim

    def _set_display_color_constant(self, stage, prim_path, rgb):
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return

        try:
            gprim = UsdGeom.Gprim(prim)
            if not gprim:
                return
            gprim.CreateDisplayColorPrimvar(UsdGeom.Tokens.constant).Set([Gf.Vec3f(*rgb)])
        except Exception as e:
            print(f"[RAN] Set displayColor failed (non-fatal) {prim_path}: {e}")

    def _is_storm_renderer_active(self):
        """Best-effort detection of whether Storm/pxr is the active renderer.

        We use this only to decide if we should clear material bindings for displayColor fallback.
        If we can't detect reliably, default to False (do NOT clear bindings).
        """
        try:
            import carb.settings

            settings = carb.settings.get_settings()
            active = settings.get("/app/renderer/active")
            if not active:
                active = settings.get("/renderer/active")
            if isinstance(active, str):
                val = active.lower()
                return ("pxr" in val) or ("storm" in val)
        except Exception:
            pass
        return False

    def _apply_environment_fallback_colors(self, stage):
        """If the environment uses materials not supported by the active renderer (e.g., Storm),
        displayColor helps avoid an all-white look.

        Under RTX, we avoid clearing material bindings by default to preserve the authored look and
        to reduce Fabric/renderer warnings. You can force clearing via config.
        """
        env_root = stage.GetPrimAtPath("/World/Environment")
        if not env_root.IsValid():
            return

        env_cfg = (self._config or {}).get("environment") or {}
        force_clear = bool(env_cfg.get("force_clear_material_bindings"))
        clear_bindings = force_clear or self._is_storm_renderer_active()

        # Heuristic: color sky-ish meshes blue and everything else neutral gray.
        colored = 0
        for prim in Usd.PrimRange(env_root):
            if prim.GetTypeName() != "Mesh":
                continue

            p = str(prim.GetPath())
            if "SkySphere" in p or "/sky" in p:
                rgb = (0.55, 0.70, 0.95)
            else:
                rgb = (0.75, 0.75, 0.75)

            if clear_bindings:
                # Some renderers ignore displayColor when a (possibly unsupported) material binding exists.
                # Clearing bindings makes Storm show colors.
                for rel_name in (
                    "material:binding",
                    "material:binding:preview",
                    "material:binding:full",
                ):
                    try:
                        if prim.HasRelationship(rel_name):
                            rel = prim.GetRelationship(rel_name)
                            if rel.IsValid():
                                rel.ClearTargets()
                    except Exception:
                        pass

            self._set_display_color_constant(stage, p, rgb)
            try:
                gprim = UsdGeom.Gprim(prim)
                gprim.CreateDisplayOpacityPrimvar(UsdGeom.Tokens.constant).Set([1.0])
            except Exception:
                pass

            colored += 1

        print(f"[RAN] Environment fallback: colored {colored} meshes")

    def _get_time_code_for_bbox(self, stage):
        """Return a pxr.Usd.TimeCode appropriate for bbox evaluation.

        Prefer the global timeline time when available; otherwise fall back
        to Usd.TimeCode.Default() for a stable, non-animated evaluation.
        """
        try:
            import omni.timeline

            timeline = omni.timeline.get_timeline_interface()
            if timeline is not None:
                seconds = float(timeline.get_current_time())
                tps = float(stage.GetTimeCodesPerSecond() or stage.GetFramesPerSecond() or 24.0)
                return Usd.TimeCode(seconds * tps)
        except Exception:
            pass

        return Usd.TimeCode.Default()

    def _compute_world_bbox(self, stage, prim):
        # NOTE: Different USD builds expose different Python signatures for BBoxCache.
        # Use positional args for maximum compatibility.
        time_code = self._get_time_code_for_bbox(stage)
        included_purposes = [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy]
        try:
            bbox_cache = UsdGeom.BBoxCache(time_code, included_purposes, True)
        except TypeError:
            # Some builds accept (time, purposes, useExtentsHint, ignoreVisibility)
            bbox_cache = UsdGeom.BBoxCache(time_code, included_purposes, True, False)
        bound = bbox_cache.ComputeWorldBound(prim)

        # Fallback: if extentsHint returns empty bounds (geometry not loaded/composed yet),
        # recompute from actual geometry with useExtentsHint=False
        size = bound.ComputeAlignedRange().GetSize()
        if max(float(size[0]), float(size[1]), float(size[2])) <= 1e-6:
            try:
                bbox_cache2 = UsdGeom.BBoxCache(time_code, included_purposes, False)
            except TypeError:
                bbox_cache2 = UsdGeom.BBoxCache(time_code, included_purposes, False, False)
            return bbox_cache2.ComputeWorldBound(prim)
        return bound

    def _scale_prim_to_target_height(self, stage, prim, target_height_m):
        try:
            world_bound = self._compute_world_bbox(stage, prim)
            bbox = world_bound.ComputeAlignedRange()
            current_height = float(bbox.GetSize()[1])

            # If Y-axis is zero (after rotation or geometry not fully loaded), use largest dimension
            if current_height <= 1e-6:
                sizes = [float(bbox.GetSize()[i]) for i in range(3)]
                current_height = max(sizes)
                if current_height <= 1e-6:
                    print(f"[RAN] Auto-scale SKIPPED '{prim.GetPath()}': bbox is zero (geometry not loaded?)")
                    return
                print(f"[RAN] Auto-scale '{prim.GetPath()}': Y-dim=0, using max-dim={current_height:.3f}")

            meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage) or 1.0)
            target_height_units = float(target_height_m) / meters_per_unit
            scale_factor = target_height_units / current_height

            # Preserve any existing scale by multiplying (read existing if present)
            xformable = UsdGeom.Xformable(prim)
            existing_ops = {op.GetOpName(): op for op in xformable.GetOrderedXformOps()}
            if "xformOp:scale" in existing_ops:
                existing = existing_ops["xformOp:scale"].Get()
                self._set_xform(prim, scale=(existing[0] * scale_factor, existing[1] * scale_factor, existing[2] * scale_factor))
            else:
                self._set_xform(prim, scale=(scale_factor, scale_factor, scale_factor))

            print(f"[RAN] Auto-scale '{prim.GetPath()}': height {current_height:.3f} -> {target_height_units:.3f} (x{scale_factor:.3f})")
        except Exception as e:
            print(f"[RAN] Auto-scale failed (non-fatal): {e}")

    def _align_prim_to_ground_y(self, stage, prim, desired_ground_y):
        try:
            world_bound = self._compute_world_bbox(stage, prim)
            bbox = world_bound.ComputeAlignedRange()
            min_y = float(bbox.GetMin()[1])

            xformable = UsdGeom.Xformable(prim)
            existing_ops = {op.GetOpName(): op for op in xformable.GetOrderedXformOps()}

            current_translate = None
            if "xformOp:translate" in existing_ops:
                t = existing_ops["xformOp:translate"].Get()
                current_translate = (float(t[0]), float(t[1]), float(t[2]))
            else:
                current_translate = (0.0, 0.0, 0.0)

            delta_y = float(desired_ground_y) - min_y
            if abs(delta_y) < 1e-6:
                return

            self._set_xform(prim, translate=(current_translate[0], current_translate[1] + delta_y, current_translate[2]))
        except Exception as e:
            print(f"[RAN] Ground align failed (non-fatal): {e}")

    def _set_xform(self, prim, translate=None, scale=None, rotate_xyz_deg=None):
        """Set translate/scale/rotateXYZ. Detect existing xformOp precision and match it."""
        xformable = UsdGeom.Xformable(prim)

        # Check if xformOps already exist (from CreatePrimCommand)
        existing_ops = {op.GetOpName(): op for op in xformable.GetOrderedXformOps()}

        if translate is not None:
            if "xformOp:translate" in existing_ops:
                op = existing_ops["xformOp:translate"]
                # Match existing precision
                if op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
                    op.Set(Gf.Vec3f(*translate))
                else:
                    op.Set(Gf.Vec3d(*translate))
            else:
                xformable.AddTranslateOp(
                    precision=UsdGeom.XformOp.PrecisionDouble
                ).Set(Gf.Vec3d(*translate))

        if scale is not None:
            if "xformOp:scale" in existing_ops:
                op = existing_ops["xformOp:scale"]
                if op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
                    op.Set(Gf.Vec3f(*scale))
                else:
                    op.Set(Gf.Vec3d(*scale))
            else:
                xformable.AddScaleOp(
                    precision=UsdGeom.XformOp.PrecisionFloat
                ).Set(Gf.Vec3f(*scale))

        if rotate_xyz_deg is not None:
            if "xformOp:rotateXYZ" in existing_ops:
                op = existing_ops["xformOp:rotateXYZ"]
                op.Set(Gf.Vec3f(float(rotate_xyz_deg[0]), float(rotate_xyz_deg[1]), float(rotate_xyz_deg[2])))
            else:
                xformable.AddRotateXYZOp(
                    precision=UsdGeom.XformOp.PrecisionFloat
                ).Set(Gf.Vec3f(float(rotate_xyz_deg[0]), float(rotate_xyz_deg[1]), float(rotate_xyz_deg[2])))

    def _build_scene(self):
        print("[RAN] _build_scene() called")
        self._stop_animation()
        self._animated_ues = []
        self._clear_scene()
        self._status.text = "Building..."
        try:
            config = self._load_config()
            print(f"[RAN] Config loaded, ground: {bool(config.get('ground'))}, buildings: {len(config.get('buildings', []))}")
            self._config = config
            usd_context = omni.usd.get_context()
            stage = usd_context.get_stage()

            if stage is None:
                print("[RAN] No stage found; creating new stage...")
                usd_context.new_stage()
                stage = usd_context.get_stage()

            if stage is None:
                raise RuntimeError("Failed to create or get USD stage")

            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
            UsdGeom.SetStageMetersPerUnit(stage, 1.0)

            if not stage.GetPrimAtPath("/World").IsValid():
                UsdGeom.Xform.Define(stage, "/World")

            # Optional environment template (first stage): reference a ready-made sky/floor.
            env_cfg = (config or {}).get("environment") or {}
            env_usd = env_cfg.get("template_usd")
            if env_usd:
                env_prim = self._add_reference(stage, "/World/Environment", env_usd)
                # Some templates are authored with payloads; force-load them so the user sees
                # real geometry (occluders) rather than only a sky dome/ground.
                try:
                    if env_prim is not None and env_prim.IsValid():
                        env_prim.Load()
                except Exception as e:
                    print(f"[RAN] Environment payload load skipped (non-fatal): {e}")
                self._apply_environment_fallback_colors(stage)

            self._build_lights(stage)

            render_only_gnb = bool((config or {}).get("render_only_gnb"))
            if render_only_gnb:
                print("[RAN] render_only_gnb=true: skipping ground/buildings/UEs")

            skip_buildings = bool((config or {}).get("skip_buildings"))
            skip_ues = bool((config or {}).get("skip_ues"))

            # If we use an environment template, skip our procedural ground to avoid overlap.
            if (not env_usd) and (not render_only_gnb):
                self._build_ground(stage, DEFAULT_GROUND_CONFIG)

            if (not render_only_gnb) and (not skip_buildings):
                for b in config["buildings"]:
                    self._build_building(stage, b)
                for o in config.get("obstacles", []):
                    self._build_building(stage, o)
            for g in config["gnbs"]:
                self._build_gnb(stage, g)

            if (not render_only_gnb) and (not skip_ues):
                for u in config["ues"]:
                    self._build_ue(stage, u)

            self._frame_camera(config)

            if render_only_gnb:
                self._status.text = f"Done! {len(config['gnbs'])} gNBs (render_only_gnb=true)"
            else:
                if skip_buildings:
                    b_count = 0
                    o_count = 0
                else:
                    b_count = len(config.get("buildings") or [])
                    o_count = len(config.get("obstacles") or [])
                u_count = 0 if skip_ues else len(config.get("ues") or [])
                self._status.text = f"Done! {b_count} buildings, {o_count} obstacles, {len(config['gnbs'])} gNBs, {u_count} UEs"
            print("[RAN] Scene build complete")

            if self._animated_ues:
                self._start_animation()

        except Exception as e:
            self._status.text = f"Error: {e}"
            print(f"[RAN] Error: {e}")
            import traceback
            traceback.print_exc()

    def _build_lights(self, stage):
        """Create a distant sun light so the scene is visible."""
        try:
            from pxr import UsdLux
        except ImportError:
            print("[RAN] UsdLux not available, skipping light creation")
            return

        light_path = "/World/SunLight"
        existing_light = stage.GetPrimAtPath(light_path)
        if existing_light.IsValid():
            print("[RAN] SunLight already exists, updating intensity")
            # Update intensity if it already exists
            try:
                intensity_attr = existing_light.GetAttribute("inputs:intensity")
                if intensity_attr:
                    intensity_attr.Set(3000.0)
            except:
                pass
            return

        # Create distant light using UsdLux API
        try:
            light = UsdLux.DistantLight.Define(stage, light_path)
            if not light or not light.GetPrim().IsValid():
                print("[RAN] Failed to create distant light (Define returned invalid prim)")
                return

            # Set intensity and angle
            light.GetIntensityAttr().Set(3000.0)
            light.GetAngleAttr().Set(0.53)

            # Rotate -45deg on X so light comes from upper direction
            light_prim = light.GetPrim()
            xformable = UsdGeom.Xformable(light_prim)
            xformable.AddRotateXYZOp(
                precision=UsdGeom.XformOp.PrecisionFloat
            ).Set(Gf.Vec3f(-45.0, 0.0, 0.0))

            print("[RAN] SunLight created with intensity 3000")
        except Exception as e:
            print(f"[RAN] Failed to create distant light: {e}")

    def _frame_camera(self, config=None):
        """Auto-frame the viewport camera to fit key prims (UE + gNB) for better visibility."""
        try:
            import omni.usd
            stage = omni.usd.get_context().get_stage()

            # Build a list of candidate camera prim paths. Different Kit versions and templates
            # use different camera prims, and some FramePrimsCommand signatures REQUIRE prim_to_move.
            camera_candidates = []
            try:
                import omni.kit.viewport.utility as vp_utils

                vp_window = vp_utils.get_active_viewport_window()
                if vp_window is not None and hasattr(vp_window, "viewport_api"):
                    cam_path = str(getattr(vp_window.viewport_api, "camera_path", "") or "").strip()
                    if cam_path:
                        camera_candidates.append(cam_path)
            except Exception:
                pass

            camera_candidates.extend(
                [
                    "/OmniverseKit_Persp",
                    "/OmniverseKit_Top",
                    "/OmniverseKit_Front",
                    "/OmniverseKit_Right",
                ]
            )

            # De-dup while preserving order.
            seen = set()
            camera_candidates = [c for c in camera_candidates if (c not in seen and not seen.add(c))]

            prims_to_frame = []
            if config:
                for b in (config.get("buildings") or []):
                    p = f"/World/{b.get('name')}"
                    if stage.GetPrimAtPath(p).IsValid():
                        prims_to_frame.append(Sdf.Path(p))
                for g in (config.get("gnbs") or []):
                    p = f"/World/{g.get('name')}"
                    if stage.GetPrimAtPath(p).IsValid():
                        prims_to_frame.append(Sdf.Path(p))
                for u in (config.get("ues") or []):
                    p = f"/World/{u.get('name')}"
                    if stage.GetPrimAtPath(p).IsValid():
                        prims_to_frame.append(Sdf.Path(p))

            # Also include the referenced environment so the user can actually see the template
            # (sky/floor) after framing.
            if stage.GetPrimAtPath("/World/Environment/ground").IsValid():
                prims_to_frame.append(Sdf.Path("/World/Environment/ground"))
            elif stage.GetPrimAtPath("/World/Environment").IsValid():
                prims_to_frame.append(Sdf.Path("/World/Environment"))

            if not prims_to_frame and stage.GetPrimAtPath("/World").IsValid():
                prims_to_frame = [Sdf.Path("/World")]

            if prims_to_frame:
                # Preferred: viewport utility framing (more stable across Kit versions).
                try:
                    import omni.kit.viewport.utility as vp_utils

                    vp_window = vp_utils.get_active_viewport_window()
                    viewport_api = getattr(vp_window, "viewport_api", None) if vp_window is not None else None
                    vp_utils.frame_viewport_prims(
                        viewport_api=viewport_api,
                        prims=[str(p) for p in prims_to_frame],
                    )
                    return
                except Exception:
                    pass

                last_err = None

                # Prefer the signature that includes prim_to_move.
                for cam in camera_candidates:
                    try:
                        omni.kit.commands.execute(
                            "FramePrimsCommand",
                            prim_to_move=Sdf.Path(cam),
                            prims_to_frame=prims_to_frame,
                            zoom=0.55,
                        )
                        return
                    except Exception as e:
                        last_err = e

                # Fallback: older Kit builds where prim_to_move is optional/unsupported.
                try:
                    omni.kit.commands.execute(
                        "FramePrimsCommand",
                        prims_to_frame=prims_to_frame,
                        zoom=0.55,
                    )
                    return
                except Exception as e:
                    last_err = e

                if last_err is not None:
                    raise last_err
        except Exception as e:
            print(f"[RAN] Frame camera failed (non-fatal): {e}")

    def _start_animation(self):
        if self._animating or not self._animated_ues:
            if not self._animated_ues:
                self._status.text = "No UEs with waypoints to animate"
            return
        import omni.kit.app
        self._animation_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_animation_update, name="ran.ue.animation"
        )
        self._animating = True
        self._status.text = f"Animating {len(self._animated_ues)} UEs..."
        print(f"[RAN] Animation started: {len(self._animated_ues)} UEs")

    def update_trajectory(self, name, waypoints, speed_mps=None, loop=True):
        """Replace waypoints for a UE at runtime. Upserts into _animated_ues
        and auto-starts the animation subscription if not already running.
        Safe to call from the update loop (thread context of api command queue)."""
        prim_path = f"/World/{name}"
        wps = [[float(c) for c in wp] for wp in (waypoints or [])]
        for ue in self._animated_ues:
            if ue["prim_path"] == prim_path:
                ue["waypoints"] = wps
                if speed_mps is not None:
                    ue["speed"] = float(speed_mps)
                ue["dist"] = 0.0
                ue["direction"] = 1
                ue["_path_len"] = None
                ue["_seg_cum"] = None
                ue["loop"] = bool(loop)
                break
        else:
            self._animated_ues.append({
                "prim_path": prim_path,
                "waypoints": wps,
                "speed": float(speed_mps) if speed_mps is not None else 1.0,
                "dist": 0.0,
                "direction": 1,
                "loop": bool(loop),
            })
        self._start_animation()
        print(f"[RAN] Trajectory updated for {name}: {len(wps)} waypoints")

    def move_ue(self, name, x, z, y=None):
        """Teleport a UE to (x, y?, z). Keeps current Y translate if y is None.
        Does NOT touch animation waypoints — just overrides current position."""
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(f"/World/{name}")
        if not prim.IsValid():
            print(f"[RAN] move_ue: UE '{name}' not found")
            return

        # Get current Y if not specified
        yv = float(y or 0.0)
        if y is None:
            xformable = UsdGeom.Xformable(prim)
            for op in xformable.GetOrderedXformOps():
                if op.GetOpName() == "xformOp:translate":
                    old = op.Get()
                    if old is not None:
                        yv = float(old[1])
                    break

        # Use _set_xform to handle xformOp creation or update
        self._set_xform(prim, translate=(float(x), yv, float(z)))
        print(f"[RAN] move_ue: '{name}' → ({float(x):.1f}, {yv:.1f}, {float(z):.1f})")

    def push_signal(self, name, serving_cell=None, rsrp_dbm=None,
                    sinr_db=None, rsrp_map=None):
        """Write ran:* custom attributes on a UE prim. mitlab.ran.labels reads
        these every frame to render the billboard text above the UE."""
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(f"/World/{name}")
        if not prim.IsValid():
            print(f"[RAN] push_signal: UE '{name}' not found")
            return
        if serving_cell is not None:
            prim.CreateAttribute(
                "ran:serving_cell", Sdf.ValueTypeNames.String, False
            ).Set(str(serving_cell))
        if rsrp_dbm is not None:
            prim.CreateAttribute(
                "ran:rsrp_dbm", Sdf.ValueTypeNames.Float, False
            ).Set(float(rsrp_dbm))
        if sinr_db is not None:
            prim.CreateAttribute(
                "ran:sinr_db", Sdf.ValueTypeNames.Float, False
            ).Set(float(sinr_db))
        if isinstance(rsrp_map, dict):
            prim.CreateAttribute(
                "ran:rsrp_map", Sdf.ValueTypeNames.String, False
            ).Set(json.dumps(rsrp_map))

    def update_gnb(self, name, changes):
        """Apply gNB property changes sent from backend.

        `changes` keys (all optional):
          - power_dbm, active        — stored in _config, feeds HUD label next
                                       time _get_gnb_config_map() is read.
          - frequency_ghz, bandwidth_mhz — same (label shows freq/bw).
          - position [x,y,z] or {x,y,z} — moves Tower + Antenna prims by
                                       rewriting their xformOp:translate.

        Labels extension is subscribed to Usd.Notice.ObjectsChanged, so touching
        any child prim's attribute fires a redraw even when we only change
        non-visible fields like power_dbm.
        """
        if not self._config or not changes:
            return
        gnbs = self._config.get("gnbs") or []
        target = next((g for g in gnbs if g.get("name") == name), None)
        if target is None:
            print(f"[RAN] update_gnb: gNB '{name}' not in config")
            return

        # --- Mutate config in place (HUD label reads this) ---
        for k in ("power_dbm", "active", "frequency_ghz", "bandwidth_mhz"):
            if changes.get(k) is not None:
                target[k] = changes[k]

        new_pos = changes.get("position")
        if new_pos is not None:
            if isinstance(new_pos, dict):
                px = float(new_pos.get("x", target["position"][0]))
                py = float(new_pos.get("y", target["position"][1]))
                pz = float(new_pos.get("z", target["position"][2]))
            else:
                px, py, pz = float(new_pos[0]), float(new_pos[1]), float(new_pos[2])
            target["position"] = [px, py, pz]

            # --- Reposition Tower + Antenna USD prims ---
            stage = omni.usd.get_context().get_stage()
            scale = float(target.get("scale") or 1.0)
            height = py * scale
            ant_radius = 6.0 * scale

            tower = stage.GetPrimAtPath(f"/World/{name}/Tower")
            if tower.IsValid():
                self._set_xform(
                    tower,
                    translate=(px, height / 2.0, pz),
                    scale=(15.0 * scale, height, 15.0 * scale),
                )
            ant = stage.GetPrimAtPath(f"/World/{name}/Antenna")
            if ant.IsValid():
                self._set_xform(ant, translate=(px, height + ant_radius, pz))

        # Force a Usd.Notice to fire so HUD label refreshes (needed for
        # non-positional changes — mutating _config alone doesn't touch USD).
        stage = omni.usd.get_context().get_stage()
        gnb_prim = stage.GetPrimAtPath(f"/World/{name}")
        if gnb_prim.IsValid():
            gnb_prim.CreateAttribute("ran:updated_at", Sdf.ValueTypeNames.Float, True).Set(
                float(time.monotonic())
            )

        print(f"[RAN] update_gnb: {name} applied {list(changes.keys())}")

    def _stop_animation(self):
        if self._animation_sub is not None:
            self._animation_sub = None
        self._animating = False
        self._status.text = "Animation stopped"
        print("[RAN] Animation stopped")

    def _on_animation_update(self, event):
        dt = float(event.payload.get("dt", 0.016))
        stage = omni.usd.get_context().get_stage()

        for ue in self._animated_ues:
            wps = ue["waypoints"]
            if len(wps) < 2:
                continue

            path_len = ue.get("_path_len")
            seg_cum = ue.get("_seg_cum")
            if path_len is None:
                lengths = []
                for k in range(len(wps) - 1):
                    dx = wps[k+1][0] - wps[k][0]
                    dy = wps[k+1][1] - wps[k][1]
                    dz = wps[k+1][2] - wps[k][2]
                    lengths.append(math.sqrt(dx*dx + dy*dy + dz*dz))
                seg_cum = []
                s = 0.0
                for l in lengths:
                    seg_cum.append(s)
                    s += l
                seg_cum.append(s)
                path_len = s
                ue["_path_len"] = path_len
                ue["_seg_cum"] = seg_cum
                if path_len < 0.001:
                    continue

            ue["dist"] += ue["speed"] * dt * ue["direction"]

            if ue["dist"] >= path_len:
                ue["dist"] = 2.0 * path_len - ue["dist"]
                ue["direction"] = -1
            elif ue["dist"] <= 0.0:
                ue["dist"] = -ue["dist"]
                ue["direction"] = 1

            ue["dist"] = max(0.0, min(ue["dist"], path_len))

            d = ue["dist"]
            seg = 0
            for k in range(len(seg_cum) - 1):
                if seg_cum[k+1] >= d:
                    seg = k
                    break
            else:
                seg = len(wps) - 2

            seg_start = seg_cum[seg]
            seg_length = seg_cum[seg+1] - seg_start
            t = (d - seg_start) / seg_length if seg_length > 0.001 else 0.0
            t = max(0.0, min(1.0, t))

            A, B = wps[seg], wps[seg+1]
            pos = (
                A[0] + t * (B[0] - A[0]),
                A[1] + t * (B[1] - A[1]),
                A[2] + t * (B[2] - A[2]),
            )

            prim = stage.GetPrimAtPath(ue["prim_path"])
            if prim.IsValid():
                self._set_xform(prim, translate=pos)

    def _clear_scene(self):
        self._stop_animation()
        self._animated_ues = []
        stage = omni.usd.get_context().get_stage()
        world = stage.GetPrimAtPath("/World")
        if world.IsValid():
            children = [child.GetPath() for child in world.GetChildren()]
            for child_path in children:
                stage.RemovePrim(child_path)
            self._status.text = "Scene cleared"
        else:
            self._status.text = "Nothing to clear"

    def _build_ground(self, stage, config):
        path = "/World/Ground"
        sx = float(config["size"][0])
        sz = float(config["size"][1])

        print(f"[RAN] Creating Ground at {path}...")
        prim = UsdGeom.Cube.Define(stage, path).GetPrim()
        print(f"[RAN] Ground prim valid: {prim.IsValid()}")
        if prim.IsValid():
            UsdGeom.Cube(prim).GetSizeAttr().Set(1.0)
            self._set_xform(prim, translate=(0, -0.5, 0), scale=(sx, 1.0, sz))
            UsdGeom.Gprim(prim).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(0.3, 0.5, 0.3)])
            print(f"[RAN] Ground created: {config['size']}")
        else:
            print(f"[RAN] Ground prim not valid!")

    def _build_building(self, stage, config):
        name = config["name"]
        pos = config["position"]
        size = config["size"]
        color = config.get("color", [0.75, 0.75, 0.75])  # Default gray if not specified

        building_usd = config.get("usd")

        container_path = f"/World/{_to_prim_name(name)}"

        # If configured, use an external building USD reference.
        if building_usd:
            # Use a stable container prim for translation / ground-align.
            # Put the referenced asset under a child prim so we can rotate/scale
            # without affecting world translation order.
            UsdGeom.Xform.Define(stage, container_path)
            container_prim = stage.GetPrimAtPath(container_path)
            if container_prim.IsValid():
                self._set_xform(
                    container_prim,
                    translate=(float(pos[0]), float(pos[1]), float(pos[2])),
                )

            asset_path = f"{container_path}/Asset"
            asset_prim = self._add_reference(stage, asset_path, building_usd)
            if asset_prim is not None and asset_prim.IsValid():
                rot = config.get("rotation_xyz_deg")
                if rot is not None and len(rot) == 3:
                    self._set_xform(
                        asset_prim,
                        rotate_xyz_deg=(float(rot[0]), float(rot[1]), float(rot[2])),
                    )

                # Optional scale controls:
                # - `scale`: explicit XYZ scale
                # - `target_height_m`: auto-scale to a desired height
                scale = config.get("scale")
                if scale and len(scale) == 3:
                    self._set_xform(
                        asset_prim,
                        scale=(float(scale[0]), float(scale[1]), float(scale[2])),
                    )
                else:
                    target_h = config.get("target_height_m")
                    if target_h is not None:
                        self._scale_prim_to_target_height(stage, asset_prim, target_height_m=float(target_h))

            # Best-effort: align referenced asset to ground (move container).
            if container_prim.IsValid():
                self._align_prim_to_ground_y(stage, container_prim, desired_ground_y=float(pos[1]))

            print(f"[RAN] Building '{name}' as USD reference")
            return

        cube_path = f"{container_path}/Mesh"

        UsdGeom.Xform.Define(stage, container_path)
        print(f"[RAN] Creating Building '{name}' cube at {cube_path}...")
        prim = UsdGeom.Cube.Define(stage, cube_path).GetPrim()
        print(f"[RAN] Building '{name}' prim valid: {prim.IsValid()}")

        if prim.IsValid():
            UsdGeom.Cube(prim).GetSizeAttr().Set(1.0)
            self._set_xform(prim,
                translate=(pos[0], size[1] / 2.0, pos[2]),
                scale=(size[0], size[1], size[2]))
            UsdGeom.Gprim(prim).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(*color)])
            print(f"[RAN] Building '{name}' at {pos}, size {size}")
        else:
            print(f"[RAN] Building '{name}' prim not valid!")

    def _build_gnb(self, stage, config):
        name = config["name"]
        pos = config["position"]
        color = config["color"]
        # Visual scaling: allow per-gNB scale override, otherwise use global config.
        global_scale = float((self._config or {}).get("gnb_visual_scale") or 1.0)
        gnb_scale = float(config.get("scale") or global_scale or 1.0)
        # Support target_height_m for consistent sizing with buildings
        target_h = config.get("target_height_m")
        if target_h is not None:
            height = float(target_h)
        else:
            height = float(pos[1]) * gnb_scale * 4.0

        container_path = f"/World/{_to_prim_name(name)}"
        UsdGeom.Xform.Define(stage, container_path)

        # Triangular pyramid tower (cone with large base)
        cone_path = f"{container_path}/Tower"
        omni.kit.commands.execute("CreatePrimCommand",
            prim_type="Cone", prim_path=cone_path)
        cone = stage.GetPrimAtPath(cone_path)
        if cone.IsValid():
            cone_geom = UsdGeom.Cone(cone)
            cone_geom.GetHeightAttr().Set(1.0)
            cone_geom.GetRadiusAttr().Set(1.0)
            # USD Cone default axis is Z, rotate so tip points up (Y)
            cone_geom.GetAxisAttr().Set(UsdGeom.Tokens.y)
            # Scale: wide base and tall (height from config), with optional visual scaling.
            base_radius = 60.0 * gnb_scale
            self._set_xform(cone,
                translate=(pos[0], height / 2.0, pos[2]),
                scale=(base_radius, height, base_radius))
            UsdGeom.Gprim(cone).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(*color)])

        # Top marker sphere (antenna)
        ant_path = f"{container_path}/Antenna"
        omni.kit.commands.execute("CreatePrimCommand",
            prim_type="Sphere", prim_path=ant_path)
        ant = stage.GetPrimAtPath(ant_path)
        if ant.IsValid():
            ant_radius = 24.0 * gnb_scale
            UsdGeom.Sphere(ant).GetRadiusAttr().Set(ant_radius)
            self._set_xform(ant, translate=(pos[0], height + ant_radius, pos[2]))
            UsdGeom.Gprim(ant).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(1.0, 1.0, 0.0)])

        # Radiation "waves" (drawn as concentric rings)
        self._build_rru_waves(
            stage=stage,
            parent_path=container_path,
            center=(float(pos[0]), float(height + (24.0 * gnb_scale)), float(pos[2])),
            color=(1.0, 0.9, 0.2),
            scale=gnb_scale,
        )

        # Support both formats: 'frequency_ghz' (from DB) or 'freq_mhz' (from API)
        freq_ghz = config.get('frequency_ghz') or (config.get('freq_mhz', 0) / 1000.0)
        print(f"[RAN] gNB '{name}' at {pos}, freq={freq_ghz}GHz")

    def _build_ue(self, stage, config):
        name = config["name"]
        pos = config["position"]
        color = config["color"]

        container_path = f"/World/{_to_prim_name(name)}"

        # If configured, use a real character USD as UE.
        ue_asset_cfg = (self._config or {}).get("ue_asset") or {}
        ue_asset_usd = config.get("usd") or ue_asset_cfg.get("usd")
        if ue_asset_usd:
            prim = self._add_reference(stage, container_path, ue_asset_usd)
            if prim is not None and prim.IsValid():
                self._set_xform(prim, translate=(float(pos[0]), float(pos[1]), float(pos[2])))
                target_height_m = float(config.get("target_height_m") or ue_asset_cfg.get("target_height_m") or 34.0)
                self._scale_prim_to_target_height(stage, prim, target_height_m=target_height_m)
                self._align_prim_to_ground_y(stage, prim, desired_ground_y=float(pos[1]))
            print(f"[RAN] UE '{name}' as character reference")

            waypoints = config.get("waypoints")
            if waypoints and len(waypoints) >= 2:
                self._animated_ues.append({
                    "prim_path": container_path,
                    "waypoints": [[float(c) for c in wp] for wp in waypoints],
                    "speed": float(config.get("speed_mps", 1.0)),
                    "dist": 0.0,
                    "direction": 1,
                })
                print(f"[RAN] UE '{name}' registered for animation: {len(waypoints)} waypoints, {config.get('speed_mps', 1.0)} m/s")
            return

        # Fallback: UE as a simple "person": cylinder body + sphere head
        body_path = f"{container_path}/Body"
        head_path = f"{container_path}/Head"

        container = UsdGeom.Xform.Define(stage, container_path)
        # Add translate op to container so move_ue can work
        self._set_xform(container.GetPrim(), translate=(float(pos[0]), float(pos[1]), float(pos[2])))
        print(f"[RAN] _build_ue: container xform configured for '{name}' at {pos}")

        body_height = 28.0
        body_radius = 5.0
        head_radius = 4.5

        omni.kit.commands.execute("CreatePrimCommand",
            prim_type="Cylinder", prim_path=body_path)
        body = stage.GetPrimAtPath(body_path)
        if body.IsValid():
            body_geom = UsdGeom.Cylinder(body)
            body_geom.GetHeightAttr().Set(1.0)
            body_geom.GetRadiusAttr().Set(1.0)
            body_geom.GetAxisAttr().Set(UsdGeom.Tokens.y)
            self._set_xform(
                body,
                translate=(pos[0], body_height / 2.0, pos[2]),
                scale=(body_radius, body_height, body_radius),
            )
            UsdGeom.Gprim(body).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(*color)])

        omni.kit.commands.execute("CreatePrimCommand",
            prim_type="Sphere", prim_path=head_path)
        head = stage.GetPrimAtPath(head_path)
        if head.IsValid():
            UsdGeom.Sphere(head).GetRadiusAttr().Set(head_radius)
            self._set_xform(head, translate=(pos[0], body_height + head_radius, pos[2]))
            UsdGeom.Gprim(head).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant).Set([Gf.Vec3f(1.0, 0.9, 0.7)])

        print(f"[RAN] UE '{name}' at {pos}")

        waypoints = config.get("waypoints")
        if waypoints and len(waypoints) >= 2:
            self._animated_ues.append({
                "prim_path": container_path,
                "waypoints": [[float(c) for c in wp] for wp in waypoints],
                "speed": float(config.get("speed_mps", 1.0)),
                "dist": 0.0,
                "direction": 1,
            })
            print(f"[RAN] UE '{name}' registered for animation: {len(waypoints)} waypoints, {config.get('speed_mps', 1.0)} m/s")

    def _build_rru_waves(self, stage, parent_path, center, color, scale=1.0):
        """Draw AAU/RRU-like radiation waves as concentric rings using BasisCurves."""
        cx, cy, cz = center
        s = float(scale) if scale is not None else 1.0
        radii = [14.0 * s, 22.0 * s, 30.0 * s]
        segments = 48
        width = 0.8 * s

        for idx, radius in enumerate(radii, start=1):
            curve_path = f"{parent_path}/Wave_{idx}"
            existing = stage.GetPrimAtPath(curve_path)
            if existing.IsValid():
                curve = UsdGeom.BasisCurves(existing)
            else:
                curve = UsdGeom.BasisCurves.Define(stage, curve_path)
            points = []
            for s in range(segments + 1):
                theta = 2.0 * math.pi * (s / segments)
                x = cx + radius * math.cos(theta)
                z = cz + radius * math.sin(theta)
                points.append(Gf.Vec3f(x, cy, z))

            curve.GetPointsAttr().Set(points)
            curve.GetCurveVertexCountsAttr().Set([len(points)])
            curve.GetTypeAttr().Set(UsdGeom.Tokens.linear)

            # Avoid RTX Hydra warnings about invalid widths primvar:
            # Hydra sometimes interprets widths as vertex-interpolated; ensure we provide
            # one width per point and set interpolation via the proper Curves API.
            prim = curve.GetPrim()
            try:
                # Clean up any stray property we may have authored in older builds.
                if prim.HasProperty("widthsInterpolation"):
                    prim.RemoveProperty("widthsInterpolation")
            except Exception:
                pass

            try:
                UsdGeom.Curves(prim).SetWidthsInterpolation(UsdGeom.Tokens.vertex)
            except Exception:
                pass

            curve.GetWidthsAttr().Set(Vt.FloatArray([float(width)] * len(points)))
            UsdGeom.Gprim(curve.GetPrim()).CreateDisplayColorPrimvar(
                UsdGeom.Tokens.constant
            ).Set([Gf.Vec3f(*color)])
