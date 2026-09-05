from django.urls import path
from .views import (
    audits_list_create_view,
    audit_detail_view,
    audit_demarrer_view,
    audit_pause_view,
    audit_arreter_view,
    audit_terminer_view,
    audit_etape_update_view,
    audit_callback_n8n_view,
    audit_rapport_page_view,
    audit_historique_view,
    execution_rapport_page_view
)

app_name = 'audits'

urlpatterns = [
    path('', audits_list_create_view, name='list-create'),
    path('<uuid:audit_id>/', audit_detail_view, name='detail'),
    path('<uuid:audit_id>/demarrer/', audit_demarrer_view, name='demarrer'),
    path('<uuid:audit_id>/pause/', audit_pause_view, name='pause'),
    path('<uuid:audit_id>/arreter/', audit_arreter_view, name='arreter'),
    path('<uuid:audit_id>/terminer/', audit_terminer_view, name='terminer'),
    path('<uuid:audit_id>/callback/', audit_callback_n8n_view, name='callback'),
    path('callback/', audit_callback_n8n_view, name='callback-global'),
    path('<uuid:audit_id>/rapport-page/', audit_rapport_page_view, name='rapport-page'),
    path('<uuid:audit_id>/historique/', audit_historique_view, name='historique'),
    path('executions/<uuid:execution_id>/rapport-page/', execution_rapport_page_view, name='execution-rapport-page'),
    path('etapes/<uuid:etape_id>/', audit_etape_update_view, name='update-etape'),
]



