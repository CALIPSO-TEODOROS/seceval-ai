from django.urls import path
from .views import (
    reports_list_create_view,
    report_detail_view,
    report_generer_view,
    report_valider_view,
    report_publier_view,
    report_telecharger_view
)

app_name = 'reports'

urlpatterns = [
    path('', reports_list_create_view, name='list-create'),
    path('<uuid:report_id>/', report_detail_view, name='detail'),
    path('<uuid:report_id>/generer/', report_generer_view, name='generer'),
    path('<uuid:report_id>/valider/', report_valider_view, name='valider'),
    path('<uuid:report_id>/publier/', report_publier_view, name='publier'),
    path('<uuid:report_id>/telecharger/', report_telecharger_view, name='telecharger'),
]
