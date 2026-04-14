from django.contrib import admin
from .models import PayrollEmployeeProfile, AttendanceSummary, PayrollRecord

@admin.register(PayrollEmployeeProfile)
class PayrollEmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('employee', 'base_hourly_rate', 'overtime_hourly_rate')

@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_period_start', 'payroll_period_end', 'total_regular_hours')

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_period_start', 'payroll_period_end', 'net_pay')