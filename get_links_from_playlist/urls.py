from django.urls import path
from . import views

urlpatterns = [
    path(
        "to-file/", views.get_playlist_links_to_file, name="get_playlist_links_to_file"
    ),
    path(
        "as-json/", views.get_playlist_links_as_json, name="get_playlist_links_as_json"
    ),
]
