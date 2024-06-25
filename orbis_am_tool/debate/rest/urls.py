from django.urls import path, include
from rest_framework.routers import DefaultRouter

from debate.rest import views


router = DefaultRouter()
router.register(r"author", views.AuthorView, basename="author")
router.register(r"debate", views.DebateView, basename="debate")
router.register(r"source", views.SourceView, basename="source")
router.register(r"statement", views.StatementView, basename="statement")


urlpatterns = [
    path("", include(router.urls)),
]
