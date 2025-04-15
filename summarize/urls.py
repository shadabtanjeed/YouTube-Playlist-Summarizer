from django.urls import path
from . import views

urlpatterns = [
    path("video/", views.get_video_summary, name="get_video_summary"),
    path("test-connection/", views.test_api_connection, name="test_api_connection"),
    path("playlist/", views.summarize_playlist, name="summarize_playlist"),
]
