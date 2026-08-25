from django.urls import path
from .views import logs_list_create_view, log_detail_view

app_name = 'logs_app'

urlpatterns = [
    path('', logs_list_create_view, name='list-create'),
    path('<uuid:log_id>/', log_detail_view, name='detail'),
]
