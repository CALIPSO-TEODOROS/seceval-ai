from django.urls import path
from .views import (
    notifications_list_create_view,
    notification_detail_view,
    notification_envoyer_view
)

app_name = 'notifications_app'

urlpatterns = [
    path('', notifications_list_create_view, name='list-create'),
    path('<uuid:notification_id>/', notification_detail_view, name='detail'),
    path('<uuid:notification_id>/envoyer/', notification_envoyer_view, name='envoyer'),
]
