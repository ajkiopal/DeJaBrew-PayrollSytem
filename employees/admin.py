from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'job_title', 'role', 'is_active')
    search_fields = ('name', 'employee_id')