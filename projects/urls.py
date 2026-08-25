from django.urls import path
from .views import (
    projects_list_create_view,
    project_detail_view,
    project_archive_view,
    project_cibles_view,
    cible_verify_view,
    cible_authorizations_view
)

app_name = 'projects'

urlpatterns = [
    path('', projects_list_create_view, name='list-create'),
    path('<uuid:project_id>/', project_detail_view, name='detail'),
    path('<uuid:project_id>/archive/', project_archive_view, name='archive'),
    path('<uuid:project_id>/cibles/', project_cibles_view, name='cibles'),
    path('cibles/<uuid:cible_id>/verify/', cible_verify_view, name='verify-cible'),
    path('cibles/<uuid:cible_id>/autorisations/', cible_authorizations_view, name='cible-authorizations'),
]
