from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.overview, name='report-overview'),
    path('by-branch/', views.by_branch, name='report-by-branch'),
    path('by-status/', views.by_status, name='report-by-status'),
    path('transfers/', views.transfers, name='report-transfers'),
]
