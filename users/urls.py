from django.urls import path
from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    users_list_view,
    user_status_change_view,
    user_role_change_view,
    roles_list_view,
    role_detail_view,
    permissions_list_view,
    permission_detail_view,
    members_list_view,
    web_ui_view,
    login_page_view,
    dashboard_stats_view
)

app_name = 'users'

urlpatterns = [
    path('web/', web_ui_view, name='web-ui'),
    path('web/login/', login_page_view, name='login-page'),
    path('dashboard/stats/', dashboard_stats_view, name='dashboard-stats'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('list/', users_list_view, name='users-list'),
    path('<uuid:user_id>/status/', user_status_change_view, name='user-status-change'),
    path('<uuid:user_id>/roles/', user_role_change_view, name='user-role-change'),
    path('permissions/', permissions_list_view, name='permissions-list'),
    path('permissions/<uuid:perm_id>/', permission_detail_view, name='permission-detail'),
    path('roles/', roles_list_view, name='roles-list'),
    path('roles/<uuid:role_id>/', role_detail_view, name='role-detail'),
    path('members/', members_list_view, name='members-list'),
]

