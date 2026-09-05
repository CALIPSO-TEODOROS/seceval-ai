from django.urls import path
from .views import (
    vulns_list_create_view,
    vulns_synchroniser_view,
    vuln_detail_view,
    vuln_confirmer_view,
    vuln_faux_positif_view,
    vuln_corrigee_view,
    vuln_classifier_view,
    vuln_preuves_view,
    vuln_recommandations_view
)

app_name = 'vulns'

urlpatterns = [
    path('', vulns_list_create_view, name='list-create'),
    path('synchroniser/', vulns_synchroniser_view, name='synchroniser'),
    path('<uuid:vuln_id>/', vuln_detail_view, name='detail'),
    path('<uuid:vuln_id>/confirmer/', vuln_confirmer_view, name='confirmer'),
    path('<uuid:vuln_id>/faux-positif/', vuln_faux_positif_view, name='faux-positif'),
    path('<uuid:vuln_id>/corrigee/', vuln_corrigee_view, name='corrigee'),
    path('<uuid:vuln_id>/classifier/', vuln_classifier_view, name='classifier'),
    path('<uuid:vuln_id>/preuves/', vuln_preuves_view, name='preuves'),
    path('<uuid:vuln_id>/recommandations/', vuln_recommandations_view, name='recommandations'),
]
