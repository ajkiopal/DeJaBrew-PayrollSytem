from django.urls import path
from . import views

urlpatterns = [
    path("admin/", views.admin_schedule_home, name="admin_schedule_home"),
    path("staff/", views.staff_schedule_home, name="staff_schedule_home"),
    path("events/", views.schedule_events, name="schedule_events"),
    path("unpost/<int:event_id>/", views.unpost_schedule_event, name="unpost_schedule_event"),
]