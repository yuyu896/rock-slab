from django.urls import path
from .views import login_view, logout_view, profile_view, change_password_view

urlpatterns = [
    path('login/', login_view),
    path('logout/', logout_view),
    path('profile/', profile_view),
    path('password/', change_password_view),
]
