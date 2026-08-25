from django.contrib import admin
from .models import Projet, Cible, AutorisationCible


class CibleInline(admin.TabularInline):
    model = Cible
    extra = 1


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ('nom', 'organisation', 'statut', 'dateCreation', 'dateArchivage', 'id')
    list_filter = ('statut', 'organisation', 'dateCreation')
    search_fields = ('nom', 'organisation', 'description')
    ordering = ('-dateCreation',)
    inlines = [CibleInline]


class AutorisationCibleInline(admin.TabularInline):
    model = AutorisationCible
    extra = 1


@admin.register(Cible)
class CibleAdmin(admin.ModelAdmin):
    list_display = ('valeur', 'type', 'environnement', 'statut', 'projet', 'dateAjout', 'id')
    list_filter = ('type', 'environnement', 'statut', 'projet')
    search_fields = ('valeur', 'projet__nom')
    ordering = ('-dateAjout',)
    inlines = [AutorisationCibleInline]


@admin.register(AutorisationCible)
class AutorisationCibleAdmin(admin.ModelAdmin):
    list_display = ('cible', 'dateDebut', 'dateFin', 'testsActifsAutorises', 'est_valide_status', 'id')
    list_filter = ('testsActifsAutorises', 'dateDebut', 'dateFin')
    search_fields = ('cible__valeur', 'preuve', 'commentaire')

    def est_valide_status(self, obj):
        return obj.estValide()
    est_valide_status.boolean = True
    est_valide_status.short_description = "Autorisation Valide"
