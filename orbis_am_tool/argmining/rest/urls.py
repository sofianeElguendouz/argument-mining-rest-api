from django.urls import path, include
from rest_framework.routers import DefaultRouter

from argmining.rest import views


router = DefaultRouter()
router.register(r"components", views.ArgumentativeComponentView, basename="argumentativecomponent")


urlpatterns = [
    path("", include(router.urls)),
]
