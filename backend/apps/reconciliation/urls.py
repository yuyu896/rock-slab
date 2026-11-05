from django.urls import path

from .views import (
    ReconciliationExportView,
    ReconciliationIssueView,
    ReconciliationTaskDetailView,
    ReconciliationTaskListView,
    ReconciliationTaskPreviewView,
    ReconciliationTaskUploadView,
)

urlpatterns = [
    path('tasks', ReconciliationTaskListView.as_view()),
    path('tasks/preview', ReconciliationTaskPreviewView.as_view()),
    path('tasks/import', ReconciliationTaskUploadView.as_view()),
    path('tasks/<uuid:pk>', ReconciliationTaskDetailView.as_view()),
    path('tasks/<uuid:pk>/archive', ReconciliationTaskDetailView.as_view()),
    path('issues/<uuid:pk>', ReconciliationIssueView.as_view()),
    path('export', ReconciliationExportView.as_view()),
]
