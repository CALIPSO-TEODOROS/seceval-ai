from django.contrib import admin
from .models import Audit, PlanAudit, EtapeAudit


class EtapeAuditInline(admin.TabularInline):
    model = EtapeAudit
    extra = 1


class PlanAuditInline(admin.StackedInline):
    model = PlanAudit
    extra = 0


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('type', 'cible', 'projet', 'statut', 'scoreSecurite', 'progression', 'dateCreation', 'dateDebut', 'id')
    list_filter = ('statut', 'type', 'projet', 'dateCreation')
    search_fields = ('cible__valeur', 'projet__nom', 'lancePar__nom')
    ordering = ('-dateCreation',)
    inlines = [PlanAuditInline]


@admin.register(PlanAudit)
class PlanAuditAdmin(admin.ModelAdmin):
    list_display = ('audit', 'description', 'dateGeneration', 'id')
    search_fields = ('audit__cible__valeur', 'description')
    inlines = [EtapeAuditInline]


@admin.register(EtapeAudit)
class EtapeAuditAdmin(admin.ModelAdmin):
    list_display = ('ordre', 'nom', 'statut', 'plan', 'dateDebut', 'dateFin', 'id')
    list_filter = ('statut',)
    search_fields = ('nom', 'plan__audit__cible__valeur')
    ordering = ('plan', 'ordre')
