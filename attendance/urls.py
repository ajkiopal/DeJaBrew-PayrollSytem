from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_csv, name="upload_csv"),
    path("history/", views.import_history, name="import_history"),
]