from django.urls import re_path

from argmining.views import AnnFilesTarView

app_name = "argmining"
urlpatterns = [
    re_path(
        r"export-debate-to-brat/(?P<identifier>[0-9a-f]{16})/$",
        AnnFilesTarView.as_view(),
        name="debate-to-brat",
    ),
]
