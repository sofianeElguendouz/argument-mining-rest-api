from django.urls import path, re_path

from argmining.rest import views


urlpatterns = [
    path(
        "argument-mining-pipeline/",
        views.ArgumentMiningPipelineView.as_view(),
        name="argument-mining-pipeline",
    ),
    re_path(
        r"component/(?P<identifier>[0-9a-f]{16})/$",
        views.ArgumentativeComponentView.as_view(),
        name="component-detail",
    ),
]
