from django.urls import path
from . import views

urlpatterns = [
    path("admin-list/", views.admin_payslip_list, name="admin_payslip_list"),
    path("view/<int:record_id>/", views.view_payslip_detail, name="view_payslip_detail"),
]