from django.urls import re_path

from argmining.rest import views


urlpatterns = [
    re_path(
        r"component/(?P<identifier>[0-9a-f]{16})/$",
        views.ArgumentativeComponentView.as_view(),
        name="component-detail",
    ),
]
