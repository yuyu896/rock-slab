from django.urls import path
from . import views

urlpatterns = [
    path('branches/', views.branches, name='report-branches'),
    path('overview/', views.overview, name='report-overview'),
    path('by-branch/', views.by_branch, name='report-by-branch'),
    path('by-status/', views.by_status, name='report-by-status'),
    path('by-category/', views.by_category, name='report-by-category'),
    path('transfers/', views.transfers, name='report-transfers'),
]
