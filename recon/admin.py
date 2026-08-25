from django.contrib import admin
from .models import TechnologieDetectee, ServiceDetecte, CertificatSSL


@admin.register(TechnologieDetectee)
class TechnologieDetecteeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'version', 'categorie', 'niveauConfiance', 'audit', 'id')
    list_filter = ('categorie', 'audit')
    search_fields = ('nom', 'categorie', 'audit__cible__valeur')
    ordering = ('nom',)


@admin.register(ServiceDetecte)
class ServiceDetecteAdmin(admin.ModelAdmin):
    list_display = ('port', 'protocole', 'service', 'version', 'etat', 'audit', 'id')
    list_filter = ('protocole', 'etat', 'service')
    search_fields = ('service', 'version', 'audit__cible__valeur')
    ordering = ('port',)


@admin.register(CertificatSSL)
class CertificatSSLAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'emetteur', 'dateDebut', 'dateExpiration', 'valide', 'protocole', 'audit', 'id')
    list_filter = ('valide', 'protocole')
    search_fields = ('sujet', 'emetteur', 'audit__cible__valeur')
    ordering = ('-dateExpiration',)
