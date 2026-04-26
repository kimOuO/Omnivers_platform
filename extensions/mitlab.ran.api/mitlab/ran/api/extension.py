"""RAN API Extension (port 8080).

Slim HTTP proxy over the Kit USD stage. Owns no state; reads and mutates via
the scene.builder extension and direct stage walks.

Signal values (RSRP/SINR) are INGESTED from an external system (Omniver-RAN
backend) via POST /ue/{name}/signal and stored on the UE prim as custom attrs:
    ran:serving_cell : String
    ran:rsrp_dbm     : Float
    ran:sinr_db      : Float
    ran:rsrp_map     : String (JSON)
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import omni.ext
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui
import omni.usd
from pxr import UsdGeom

from . import ws_server

API_PORT = 8080


# ----------------------------------------------------------------------------
# Stage read helpers
# ----------------------------------------------------------------------------

def _get_translate(prim):
    xformable = UsdGeom.Xformable(prim)
    for op in xformable.GetOrderedXformOps():
        if op.GetOpName() == "xformOp:translate":
            v = op.Get()
            if v is not None:
                return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}
    return {"x": 0.0, "y": 0.0, "z": 0.0}


def _get_ue_signal(prim):
    """Read ran:* custom attrs written by POST /ue/{name}/signal."""
    result = {"serving_cell": None, "rsrp_dbm": None, "sinr_db": None, "rsrp_map": {}}
    a = prim.GetAttribute("ran:serving_cell")
    if a and a.HasValue():
        result["serving_cell"] = str(a.Get())
    a = prim.GetAttribute("ran:rsrp_dbm")
    if a and a.HasValue():
        result["rsrp_dbm"] = float(a.Get())
    a = prim.GetAttribute("ran:sinr_db")
    if a and a.HasValue():
        result["sinr_db"] = float(a.Get())
    a = prim.GetAttribute("ran:rsrp_map")
    if a and a.HasValue():
        try:
            result["rsrp_map"] = json.loads(str(a.Get()))
        except Exception:  # noqa: BLE001
            result["rsrp_map"] = {}
    return result


def _scan_stage(stage, builder=None):
    """Walk /World/* and return (gnbs, ues). builder gives config & anim map."""
    gnbs: list = []
    ues: list = []
    if stage is None:
        return gnbs, ues
    world = stage.GetPrimAtPath("/World")
    if not world.IsValid():
        return gnbs, ues

    config_gnbs = {}
    animated = {}
    if builder is not None:
        config_gnbs = {g["name"]: g for g in ((builder._config or {}).get("gnbs") or [])}
        animated = {ue["prim_path"]: ue for ue in getattr(builder, "_animated_ues", [])}

    for child in world.GetChildren():
        name = child.GetName()
        if name.startswith("gNB"):
            cfg = config_gnbs.get(name, {})
            # gNB container Xform has no translate (actual position lives on the
            # Tower/Antenna children). Read from scene config instead.
            cfg_pos = cfg.get("position")
            if cfg_pos and len(cfg_pos) == 3:
                pos = {"x": float(cfg_pos[0]), "y": float(cfg_pos[1]), "z": float(cfg_pos[2])}
            else:
                pos = _get_translate(child)
            gnbs.append({
                "name": name,
                "position": pos,
                "freq_mhz": float(cfg.get("frequency_ghz", 0) or 0) * 1000.0,
                "power_dbm": float(cfg.get("power_dbm", 0) or 0),
                "bw_hz": float(cfg.get("bandwidth_mhz", 0) or 0) * 1_000_000.0,
                "active": True,
            })
        elif name.startswith("UE"):
            sig = _get_ue_signal(child)
            anim = animated.get(str(child.GetPath()))
            ues.append({
                "name": name,
                "position": _get_translate(child),
                "serving_cell": sig["serving_cell"],
                "rsrp_dbm": sig["rsrp_dbm"],
                "sinr_db": sig["sinr_db"],
                "rsrp_map": sig["rsrp_map"],
                "speed_mps": float(anim["speed"]) if anim else None,
            })
    return gnbs, ues


# ----------------------------------------------------------------------------
# HTTP handler
# ----------------------------------------------------------------------------

class RANAPIHandler(BaseHTTPRequestHandler):
    """`self.server.ext` points back to the extension instance."""

    def log_message(self, format, *args):
        print(f"[RAN API] {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        ext = self.server.ext
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/") if path else []

        try:
            if not parts:
                self._send_json(ext.endpoints())
                return

            if parts == ["scene", "status"]:
                stage = omni.usd.get_context().get_stage()
                builder = ext._get_scene_builder()
                gnbs, ues = _scan_stage(stage, builder)
                buildings = 0
                if builder and builder._config:
                    buildings = len(builder._config.get("buildings") or [])
                self._send_json({
                    "buildings": buildings,
                    "gnbs": len(gnbs),
                    "ues": len(ues),
                    "animating": bool(getattr(builder, "_animating", False)) if builder else False,
                    "api_port": API_PORT,
                })
                return

            if parts == ["gnbs"] or (len(parts) == 2 and parts[0] == "gnb"):
                stage = omni.usd.get_context().get_stage()
                builder = ext._get_scene_builder()
                gnbs, _ = _scan_stage(stage, builder)
                if parts == ["gnbs"]:
                    self._send_json(gnbs); return
                found = next((g for g in gnbs if g["name"] == parts[1]), None)
                if found:
                    self._send_json(found)
                else:
                    self._send_json({"error": f"gNB '{parts[1]}' not found"}, 404)
                return

            if parts == ["ues"] or (len(parts) == 2 and parts[0] == "ue"):
                stage = omni.usd.get_context().get_stage()
                builder = ext._get_scene_builder()
                _, ues = _scan_stage(stage, builder)
                if parts == ["ues"]:
                    self._send_json(ues); return
                found = next((u for u in ues if u["name"] == parts[1]), None)
                if found:
                    self._send_json(found)
                else:
                    self._send_json({"error": f"UE '{parts[1]}' not found"}, 404)
                return

            # /scene/layout — full map data for frontend top-down view
            if parts == ["scene", "layout"]:
                stage = omni.usd.get_context().get_stage()
                builder = ext._get_scene_builder()
                gnbs, ues = _scan_stage(stage, builder)
                buildings = []
                if builder and builder._config:
                    for b in (builder._config.get("buildings") or []):
                        pos = b.get("position") or [0, 0, 0]
                        size = b.get("size") or [1, 1, 1]
                        buildings.append({
                            "name": b.get("name", ""),
                            "position": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
                            "size": {"x": float(size[0]), "y": float(size[1]), "z": float(size[2])},
                            "material": b.get("material"),
                        })
                ground = (builder._config or {}).get("ground", {}) if builder else {}
                self._send_json({
                    "buildings": buildings,
                    "gnbs": gnbs,
                    "ues": ues,
                    "ground": ground,
                })
                return

            self._send_json({"error": "not found", "path": self.path}, 404)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        ext = self.server.ext
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/") if path else []

        try:
            if parts == ["scene", "build"]:
                ext._enqueue("build_scene"); self._send_json({"status": "queued"}); return
            if parts == ["scene", "clear"]:
                ext._enqueue("clear_scene"); self._send_json({"status": "queued"}); return
            if parts == ["scene", "config"]:
                body = self._read_body()
                ext._runtime_config = body
                ext._enqueue("build_scene"); self._send_json({"status": "queued"}); return
            if parts == ["animation", "start"]:
                ext._enqueue("start_animation"); self._send_json({"status": "queued"}); return
            if parts == ["animation", "stop"]:
                ext._enqueue("stop_animation"); self._send_json({"status": "queued"}); return

            if len(parts) == 3 and parts[0] == "ue":
                body = self._read_body()
                name = parts[1]
                action = parts[2]
                if action == "move":
                    ext._enqueue("move_ue", name=name, **body)
                    self._send_json({"status": "queued", "ue": name}); return
                if action == "trajectory":
                    ext._enqueue("update_trajectory", name=name, **body)
                    self._send_json({"status": "queued", "ue": name}); return
                if action == "signal":
                    ext._enqueue("push_signal", name=name, **body)
                    self._send_json({"status": "queued", "ue": name}); return

            if len(parts) == 3 and parts[0] == "gnb" and parts[2] == "update":
                body = self._read_body()
                name = parts[1]
                ext._enqueue("update_gnb", name=name, changes=body)
                self._send_json({"status": "queued", "gnb": name}); return

            self._send_json({"error": "not found", "path": self.path}, 404)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, 500)


# ----------------------------------------------------------------------------
# Extension
# ----------------------------------------------------------------------------

class RANAPIExtension(omni.ext.IExt):

    def on_startup(self, ext_id):
        print("[mitlab.ran.api] Extension startup")
        self._command_queue = []
        self._queue_lock = threading.Lock()
        self._server = None
        self._server_thread = None
        self._ws_task = None
        self._ws_server = None
        self._ws_clients = set()
        self._runtime_config = None

        self._start_server()
        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._process_commands, name="ran.api.commands"
        )

        # WS push server on Kit's asyncio loop (main thread → USD-safe).
        self._ws_task = omni.kit.async_engine.run_coroutine(ws_server.serve(self))

        self._window = ui.Window("RAN API", width=280, height=80)
        with self._window.frame:
            with ui.VStack(spacing=4):
                ui.Label(f"HTTP :{API_PORT}  |  WS :{ws_server.WS_PORT}",
                         alignment=ui.Alignment.CENTER, height=30, style={"font_size": 12})

        print(f"[mitlab.ran.api] HTTP :{API_PORT}  WS :{ws_server.WS_PORT}")

    def on_shutdown(self):
        self._update_sub = None
        self._stop_server()
        # WS shutdown: close listener synchronously so port frees immediately,
        # then cancel the serve() task. Connected clients are dropped when
        # their handler coroutine is cancelled.
        srv = getattr(self, "_ws_server", None)
        if srv is not None:
            try:
                srv.close()
            except Exception as e:  # noqa: BLE001
                print(f"[mitlab.ran.api] WS close error: {e}")
            self._ws_server = None
        if self._ws_task is not None:
            try:
                self._ws_task.cancel()
            except Exception:  # noqa: BLE001
                pass
            self._ws_task = None
        if hasattr(self, "_ws_clients"):
            self._ws_clients.clear()
        print("[mitlab.ran.api] Extension shutdown")

    # --- server ---

    def _start_server(self):
        try:
            server = HTTPServer(("0.0.0.0", API_PORT), RANAPIHandler)
            server.ext = self
            self._server = server
            self._server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            self._server_thread.start()
        except Exception as e:  # noqa: BLE001
            print(f"[RAN API] Failed to start server: {e}")

    def _stop_server(self):
        if self._server:
            self._server.shutdown()
            self._server = None

    def endpoints(self):
        return {
            "name": "RAN Digital Twin API",
            "version": "0.2.0",
            "endpoints": [
                "GET  /scene/status",
                "GET  /gnbs", "GET  /gnb/{name}",
                "GET  /ues",  "GET  /ue/{name}",
                "POST /scene/build", "POST /scene/clear", "POST /scene/config",
                "POST /animation/start", "POST /animation/stop",
                "POST /ue/{name}/move       body={x,y,z}",
                "POST /ue/{name}/trajectory body={waypoints,speed_mps,loop}",
                "POST /ue/{name}/signal     body={serving_cell,rsrp_dbm,sinr_db,rsrp_map}",
                "POST /gnb/{name}/update    body={power_dbm,active,frequency_ghz,bandwidth_mhz,position}",
            ],
        }

    # --- command queue (runs on Kit update loop; USD-safe) ---

    def _enqueue(self, action, **kwargs):
        with self._queue_lock:
            self._command_queue.append({"action": action, **kwargs})

    def _process_commands(self, event):
        with self._queue_lock:
            if not self._command_queue:
                return
            cmds = list(self._command_queue)
            self._command_queue.clear()

        builder = self._get_scene_builder()
        if builder is None:
            print("[RAN API] scene.builder not ready; dropping commands")
            return

        for cmd in cmds:
            action = cmd.get("action")
            try:
                # Pure dispatcher — every action delegates straight to builder.
                # All USD mutations live in mitlab.ran.scene.builder.
                if action == "build_scene":
                    builder._build_scene()
                elif action == "clear_scene":
                    builder._clear_scene()
                elif action == "start_animation":
                    builder._start_animation()
                elif action == "stop_animation":
                    builder._stop_animation()
                elif action == "move_ue":
                    builder.move_ue(
                        name=cmd["name"],
                        x=cmd["x"], z=cmd["z"],
                        y=cmd.get("y"),
                    )
                elif action == "update_trajectory":
                    builder.update_trajectory(
                        cmd["name"],
                        cmd.get("waypoints") or [],
                        speed_mps=cmd.get("speed_mps"),
                        loop=cmd.get("loop", True),
                    )
                elif action == "push_signal":
                    builder.push_signal(
                        name=cmd["name"],
                        serving_cell=cmd.get("serving_cell"),
                        rsrp_dbm=cmd.get("rsrp_dbm"),
                        sinr_db=cmd.get("sinr_db"),
                        rsrp_map=cmd.get("rsrp_map"),
                    )
                elif action == "update_gnb":
                    builder.update_gnb(
                        name=cmd["name"],
                        changes=cmd.get("changes") or {},
                    )
                else:
                    print(f"[RAN API] Unknown action: {action}")
                    continue
                print(f"[RAN API] Executed: {action}")
            except Exception as e:  # noqa: BLE001
                print(f"[RAN API] Command error ({action}): {e}")

    def _get_scene_builder(self):
        try:
            from mitlab.ran.scene.builder.extension import RANSceneBuilderExtension
            return RANSceneBuilderExtension._instance
        except Exception:  # noqa: BLE001
            return None
