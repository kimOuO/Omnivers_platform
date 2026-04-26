"""URL routing — POST-only, /api/v0.1/{System}/{Module}/{Component}/{Element}.

System = RAN
Modules: Scene, UE, GNB, Ingest, History, Platform
Component = Actor class name
Element = action
"""
from __future__ import annotations

from django.urls import path

from main.apps.ran.actors.gnb_actor import GNBController, GNBReader
from main.apps.ran.actors.history_actor import PositionHistoryReader, SignalHistoryReader
from main.apps.ran.actors.ingest_actor import SceneIngestor, SignalIngestor
from main.apps.ran.actors.platform_actor import PlatformReporter
from main.apps.ran.actors.playback_actor import PlaybackController
from main.apps.ran.actors.scene_actor import (
    AnimationController,
    SceneController,
    SceneLayoutReader,
    SceneStateReader,
)
from main.apps.ran.actors.sim_session_actor import SimSessionController
from main.apps.ran.actors.ue_actor import UEController, UEReader

urlpatterns = [
    # ---- RAN/Scene ----
    path("RAN/Scene/SceneStateReader/read", SceneStateReader.read, name="scene_state_read"),
    path("RAN/Scene/SceneLayoutReader/read", SceneLayoutReader.read, name="scene_layout_read"),
    path("RAN/Scene/SceneController/build", SceneController.build, name="scene_build"),
    path("RAN/Scene/SceneController/clear", SceneController.clear, name="scene_clear"),
    path("RAN/Scene/AnimationController/start", AnimationController.start, name="anim_start"),
    path("RAN/Scene/AnimationController/stop", AnimationController.stop, name="anim_stop"),

    # ---- RAN/UE ----
    path("RAN/UE/UEReader/read", UEReader.read, name="ue_read"),
    path("RAN/UE/UEController/move", UEController.move, name="ue_move"),
    path("RAN/UE/UEController/trajectory", UEController.trajectory, name="ue_trajectory"),

    # ---- RAN/GNB ----
    path("RAN/GNB/GNBReader/read", GNBReader.read, name="gnb_read"),
    path("RAN/GNB/GNBController/update", GNBController.update, name="gnb_update"),

    # ---- RAN/Ingest ----
    path("RAN/Ingest/SignalIngestor/create", SignalIngestor.create, name="ingest_signal"),
    path("RAN/Ingest/SceneIngestor/create", SceneIngestor.create, name="ingest_scene"),

    # ---- RAN/History ----
    path("RAN/History/PositionHistoryReader/read", PositionHistoryReader.read, name="history_position"),
    path("RAN/History/SignalHistoryReader/read", SignalHistoryReader.read, name="history_signal"),

    # ---- RAN/Platform ----
    path("RAN/Platform/PlatformReporter/create", PlatformReporter.create, name="platform_report"),

    # ---- RAN/SimSession ----
    path("RAN/SimSession/SimSessionController/create", SimSessionController.create, name="sim_session_create"),
    path("RAN/SimSession/SimSessionController/end", SimSessionController.end, name="sim_session_end"),

    # ---- RAN/SimSession/Playback ----
    path("RAN/SimSession/PlaybackController/list", PlaybackController.list, name="playback_list"),
    path("RAN/SimSession/PlaybackController/read", PlaybackController.read, name="playback_read"),
]
