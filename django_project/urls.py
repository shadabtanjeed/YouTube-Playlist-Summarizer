from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/playlist/", include("get_links_from_playlist.urls")),
    path("api/summarize/", include("summarize.urls")),
    path("summarize/", include("summarize.urls")),
    path("", RedirectView.as_view(url="summarize/", permanent=True)),
]
