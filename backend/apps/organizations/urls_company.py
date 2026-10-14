from django.urls import path
from .views import CompanyView, CompanyWechatQrView

urlpatterns = [
    path('', CompanyView.as_view()),
    path('wechat-qr/', CompanyWechatQrView.as_view()),
]
