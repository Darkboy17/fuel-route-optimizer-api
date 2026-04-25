"""URL configuration for the routes app.

The `urlpatterns` list routes URLs to views."""

from django.urls import path
from .views import RouteFuelView

# The `urlpatterns` list routes URLs to views.
urlpatterns = [
    path("route-fuel/", RouteFuelView.as_view(), name="route-fuel"),
]