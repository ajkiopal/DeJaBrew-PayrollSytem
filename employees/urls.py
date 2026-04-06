from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_employees_home, name="admin_employees_home"),
    path("<int:employee_id>/reset-password/", views.employee_reset_password, name="employee_reset_password"),
]