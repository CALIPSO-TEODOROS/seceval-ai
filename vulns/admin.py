from django.contrib import admin
from .models import Vulnerabilite, Preuve, Recommandation


class PreuveInline(admin.TabularInline):
    model = Preuve
    extra = 1


class RecommandationInline(admin.StackedInline):
    model = Recommandation
    extra = 1


@admin.register(Vulnerabilite)
class VulnerabiliteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'gravite', 'scoreCVSS', 'codeCWE', 'statut', 'audit', 'dateDetection', 'id')
    list_filter = ('gravite', 'statut', 'codeCWE', 'audit')
    search_fields = ('titre', 'description', 'codeCWE', 'audit__cible__valeur')
    ordering = ('-scoreCVSS', '-dateDetection')
    inlines = [PreuveInline, RecommandationInline]


@admin.register(Preuve)
class PreuveAdmin(admin.ModelAdmin):
    list_display = ('type', 'vulnerabilite', 'dateCreation', 'id')
    list_filter = ('type',)
    search_fields = ('contenu', 'vulnerabilite__titre')


@admin.register(Recommandation)
class RecommandationAdmin(admin.ModelAdmin):
    list_display = ('priorite', 'composantConcerne', 'vulnerabilite', 'id')
    list_filter = ('priorite',)
    search_fields = ('description', 'composantConcerne', 'vulnerabilite__titre')
