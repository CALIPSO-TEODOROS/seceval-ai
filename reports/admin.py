from django.contrib import admin
from .models import Rapport


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ('titre', 'format', 'statut', 'scoreFinal', 'audit', 'dateGeneration', 'id')
    list_filter = ('format', 'statut', 'audit')
    search_fields = ('titre', 'cheminFichier', 'audit__cible__valeur')
    ordering = ('-dateGeneration',)
