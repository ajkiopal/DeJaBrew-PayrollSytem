from django.contrib import admin
from .models import PayPeriod, PayrollRun

@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'label', 'status')
    list_filter = ('status',)

@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('period', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'period')
    
    # This allows you to delete multiple runs at once easily
    actions = ['delete_selected']