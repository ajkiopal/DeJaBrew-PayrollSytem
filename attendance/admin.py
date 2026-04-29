from django.contrib import admin

from .models import Attendance, ImportHistory

admin.site.register(Attendance)
admin.site.register(ImportHistory)