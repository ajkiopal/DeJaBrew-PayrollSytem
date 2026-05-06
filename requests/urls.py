from django.urls import path
from . import views

urlpatterns = [
    path("admin/", views.admin_requests_home, name="admin_requests_home"),
    path("staff/", views.staff_requests_home, name="staff_requests_home"),
    path("staff/create/", views.staff_request_create, name="staff_request_create"),
    path("approve/<int:request_id>/", views.approve_request, name="approve_request"),
    path("reject/<int:request_id>/", views.reject_request, name="reject_request"),
]