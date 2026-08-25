import uuid
from django.db import models
from audits.models import Audit


class TechnologieDetectee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="technologies",
        verbose_name="Audit associé"
    )
    nom = models.CharField(max_length=150, verbose_name="Nom de la technologie")
    version = models.CharField(max_length=50, blank=True, default="", verbose_name="Version")
    categorie = models.CharField(max_length=100, blank=True, default="", verbose_name="Catégorie")
    niveauConfiance = models.FloatField(default=100.0, verbose_name="Niveau de confiance (0 à 100%)")

    class Meta:
        verbose_name = "Technologie Détectée"
        verbose_name_plural = "Technologies Détectées"
        ordering = ['nom']

    def __str__(self):
        v = f" v{self.version}" if self.version else ""
        return f"{self.nom}{v} ({self.categorie}) [{self.niveauConfiance}%]"


class ServiceDetecte(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="Audit associé"
    )
    port = models.IntegerField(verbose_name="Port réseau")
    protocole = models.CharField(max_length=20, default="tcp", verbose_name="Protocole (tcp/udp)")
    service = models.CharField(max_length=100, verbose_name="Nom du service")
    version = models.CharField(max_length=100, blank=True, default="", verbose_name="Version du service")
    etat = models.CharField(max_length=50, default="open", verbose_name="État du port (open, closed, filtered)")

    class Meta:
        verbose_name = "Service Détecté"
        verbose_name_plural = "Services Détectés"
        ordering = ['port']

    def __str__(self):
        v = f" ({self.version})" if self.version else ""
        return f"Port {self.port}/{self.protocole} - {self.service}{v} [{self.etat}]"


class CertificatSSL(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="certificats_ssl",
        verbose_name="Audit associé"
    )
    sujet = models.CharField(max_length=255, verbose_name="Sujet (Subject / CN)")
    emetteur = models.CharField(max_length=255, verbose_name="Émetteur (Issuer)")
    dateDebut = models.DateField(verbose_name="Date d'émission (Not Before)")
    dateExpiration = models.DateField(verbose_name="Date d'expiration (Not After)")
    valide = models.BooleanField(default=True, verbose_name="Est valide")
    protocole = models.CharField(max_length=50, default="TLSv1.3", verbose_name="Protocole SSL/TLS")

    class Meta:
        verbose_name = "Certificat SSL/TLS"
        verbose_name_plural = "Certificats SSL/TLS"
        ordering = ['-dateExpiration']

    def __str__(self):
        status = "Valide" if self.valide else "Expiré / Invalide"
        return f"SSL Cert: {self.sujet} - Émis par {self.emetteur} [{status}]"
