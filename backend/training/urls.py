from django.urls import path

from . import views

app_name = "training"

urlpatterns = [
    path("bootstrap", views.bootstrap, name="bootstrap"),
    path("all-scenarios", views.all_scenarios, name="all-scenarios"),
    path("user-info", views.user_info, name="user-info"),
    path("recommendations", views.recommendations, name="recommendations"),
    path("training-sessions", views.start_training, name="start-training"),
    path(
        "training-sessions/<uuid:session_id>/turns",
        views.submit_turn,
        name="submit-turn",
    ),
    path(
        "training-sessions/<uuid:session_id>/turns/audio",
        views.submit_turn_audio,
        name="submit-turn-audio",
    ),
    path(
        "training-sessions/<uuid:session_id>/turns/audio/stream",
        views.turn_audio_stream,
        name="turn-audio-stream",
    ),
    path(
        "training-sessions/<uuid:session_id>/turns/stream",
        views.turn_stream,
        name="turn-stream",
    ),
    path(
        "training-sessions/<uuid:session_id>/judgment",
        views.submit_judgment,
        name="submit-judgment",
    ),
]
