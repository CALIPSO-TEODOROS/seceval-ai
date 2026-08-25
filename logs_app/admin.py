from django.contrib import admin
from .models import JournalActivite


@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display = ('action', 'ressource', 'utilisateur', 'adresseIP', 'projet', 'audit', 'dateAction', 'id')
    list_filter = ('action', 'dateAction', 'projet')
    search_fields = ('action', 'ressource', 'details', 'utilisateur__email', 'utilisateur__nom', 'adresseIP')
    ordering = ('-dateAction',)
