from django.urls import path

from analytics.api import MarketerAnalyticsDashboardView
from .views import (
    MarketerContractListCreateView,
    MarketerContractDetailView,
    MarketerContractActivateView,
    MarketerContractPauseView,
    MarketerContractResumeView,
    MarketerContractEndView,
    MarketerCommissionListView,
)


urlpatterns = [
    path("dashboard/", MarketerAnalyticsDashboardView.as_view(), name="marketer-dashboard"),
    path("contracts/", MarketerContractListCreateView.as_view(), name="marketer-contracts"),
    path("contracts/<uuid:pk>/", MarketerContractDetailView.as_view(), name="marketer-contract-detail"),
    path("contracts/<uuid:pk>/activate/", MarketerContractActivateView.as_view(), name="marketer-contract-activate"),
    path("contracts/<uuid:pk>/pause/", MarketerContractPauseView.as_view(), name="marketer-contract-pause"),
    path("contracts/<uuid:pk>/resume/", MarketerContractResumeView.as_view(), name="marketer-contract-resume"),
    path("contracts/<uuid:pk>/end/", MarketerContractEndView.as_view(), name="marketer-contract-end"),
    path("commissions/", MarketerCommissionListView.as_view(), name="marketer-commissions"),
]
