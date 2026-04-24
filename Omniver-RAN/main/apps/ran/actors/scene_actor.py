"""Scene-related actors: read overview, build/clear, animation start/stop."""
from __future__ import annotations

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.serializers.scene_serializers import (
    SceneLayoutReadSerializer,
    SceneOverviewReadSerializer,
)
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class SceneStateReader:
    """GET-style overview (buildings/gnbs/ues/animating). Reads from Kit."""

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            raw = KitBusinessService.get_scene_status()
        except Exception as e:  # noqa: BLE001
            log.error("SceneStateReader.read Kit unreachable: %s", e)
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        output = SceneOverviewReadSerializer.to_representation(raw)
        return success_response(output)


class SceneLayoutReader:
    """Full map payload (buildings + gnbs + ues + ground) for trajectory editor."""

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            raw = KitBusinessService.get_scene_layout()
        except Exception as e:  # noqa: BLE001
            log.error("SceneLayoutReader.read Kit unreachable: %s", e)
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response(SceneLayoutReadSerializer.to_representation(raw))


class SceneController:
    """Scene lifecycle commands."""

    @staticmethod
    @actor
    def build(request):  # noqa: ARG004
        try:
            KitBusinessService.build_scene()
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response({"action": "build"}, "queued")

    @staticmethod
    @actor
    def clear(request):  # noqa: ARG004
        try:
            KitBusinessService.clear_scene()
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response({"action": "clear"}, "queued")


class AnimationController:
    @staticmethod
    @actor
    def start(request):  # noqa: ARG004
        try:
            KitBusinessService.start_animation()
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response({"action": "start"}, "queued")

    @staticmethod
    @actor
    def stop(request):  # noqa: ARG004
        try:
            KitBusinessService.stop_animation()
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response({"action": "stop"}, "queued")
