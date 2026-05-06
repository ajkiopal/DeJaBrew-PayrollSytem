from django.contrib import admin
from .models import PayPeriod, PayrollRun

admin.site.register(PayrollRun)
admin.site.register(PayPeriod)