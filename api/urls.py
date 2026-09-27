from django.urls import path
from .views import ScanVerifyView

urlpatterns = [
    path('scan/verify/', ScanVerifyView.as_view(), name='scan-verify'),
]