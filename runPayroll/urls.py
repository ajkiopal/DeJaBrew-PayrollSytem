"""
URL configuration for payroll project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.payroll_run_create_page, name="payroll_run_create"),
    path("runs/<int:run_id>/", views.payroll_run_detail, name="payroll_run_detail"),
    path("periods/", views.pay_period_list_create, name="pay_periods"),
    path("periods/<int:period_id>/close/", views.pay_period_close, name="pay_period_close"),
]