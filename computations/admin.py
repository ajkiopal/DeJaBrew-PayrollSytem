from django.contrib import admin
from .models import AttendanceSummary, PayrollRecord, AdjustmentRecord

admin.site.register(AttendanceSummary)
admin.site.register(PayrollRecord)
admin.site.register(AdjustmentRecord)