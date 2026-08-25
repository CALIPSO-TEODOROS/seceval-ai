from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'canal', 'destinataire', 'statut', 'dateCreation', 'dateEnvoi', 'id')
    list_filter = ('canal', 'statut', 'dateCreation')
    search_fields = ('sujet', 'message', 'destinataire__email', 'destinataire__nom')
    ordering = ('-dateCreation',)
