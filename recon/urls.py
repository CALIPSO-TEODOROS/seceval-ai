from django.urls import path
from .views import (
    audit_recon_results_view,
    audit_recon_scan_simulation_view,
    create_technologie_view,
    create_service_view,
    create_ssl_view
)

app_name = 'recon'

urlpatterns = [
    path('audit/<uuid:audit_id>/', audit_recon_results_view, name='audit-results'),
    path('audit/<uuid:audit_id>/scan/', audit_recon_scan_simulation_view, name='audit-scan'),
    path('technologies/', create_technologie_view, name='create-technologie'),
    path('services/', create_service_view, name='create-service'),
    path('ssl/', create_ssl_view, name='create-ssl'),
]
