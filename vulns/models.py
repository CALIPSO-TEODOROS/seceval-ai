import uuid
from django.db import models
from django.utils import timezone
from audits.models import Audit


class Gravite(models.TextChoices):
    CRITIQUE = 'CRITIQUE', 'Critique (CVSS 9.0 - 10.0)'
    ELEVEE = 'ELEVEE', 'Élevée (CVSS 7.0 - 8.9)'
    MOYENNE = 'MOYENNE', 'Moyenne (CVSS 4.0 - 6.9)'
    FAIBLE = 'FAIBLE', 'Faible (CVSS 0.1 - 3.9)'
    INFORMATION = 'INFORMATION', 'Information (CVSS 0.0)'


class StatutVulnerabilite(models.TextChoices):
    NOUVELLE = 'NOUVELLE', 'Nouvelle'
    A_VERIFIER = 'A_VERIFIER', 'À vérifier'
    CONFIRMEE = 'CONFIRMEE', 'Confirmée'
    FAUX_POSITIF = 'FAUX_POSITIF', 'Faux positif'
    CORRECTION_EN_COURS = 'CORRECTION_EN_COURS', 'Correction en cours'
    CORRIGEE = 'CORRIGEE', 'Corrigée'
    RISQUE_ACCEPTE = 'RISQUE_ACCEPTE', 'Risque accepté'


class Vulnerabilite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="vulnerabilites",
        verbose_name="Audit associé"
    )
    titre = models.CharField(max_length=255, verbose_name="Titre de la vulnérabilité")
    description = models.TextField(verbose_name="Description détaillée")
    gravite = models.CharField(
        max_length=20,
        choices=Gravite.choices,
        default=Gravite.MOYENNE,
        verbose_name="Gravité / Sévérité"
    )
    confiance = models.FloatField(default=100.0, verbose_name="Niveau de confiance (0 à 100%)")
    scoreCVSS = models.FloatField(default=5.0, verbose_name="Score CVSS (0.0 à 10.0)")
    codeCWE = models.CharField(max_length=50, blank=True, default="", verbose_name="Code CWE (ex: CWE-89)")
    statut = models.CharField(
        max_length=30,
        choices=StatutVulnerabilite.choices,
        default=StatutVulnerabilite.NOUVELLE,
        verbose_name="Statut de la vulnérabilité"
    )
    dateDetection = models.DateTimeField(auto_now_add=True, verbose_name="Date de détection")

    class Meta:
        verbose_name = "Vulnérabilité"
        verbose_name_plural = "Vulnérabilités"
        ordering = ['-scoreCVSS', '-dateDetection']

    def __str__(self):
        return f"[{self.gravite}] {self.titre} ({self.codeCWE}) - {self.get_statut_display()}"

    def classifier(self, gravite=None, scoreCVSS=None, codeCWE=None):
        """
        Méthode métier classifier() :
        Met à jour la gravité, le score CVSS et/ou le code CWE de la vulnérabilité.
        """
        update_fields = []
        if gravite is not None:
            self.gravite = gravite
            update_fields.append('gravite')
        if scoreCVSS is not None:
            self.scoreCVSS = scoreCVSS
            update_fields.append('scoreCVSS')
        if codeCWE is not None:
            self.codeCWE = codeCWE
            update_fields.append('codeCWE')

        if update_fields:
            self.save(update_fields=update_fields)

        # Mettre à jour le score global de l'audit
        self.audit.calculerScore()
        self.audit.save(update_fields=['scoreSecurite'])
        return self

    def confirmer(self):
        """Méthode métier confirmer() : passe le statut en CONFIRMEE."""
        self.statut = StatutVulnerabilite.CONFIRMEE
        self.save(update_fields=['statut'])
        return self

    def marquerFauxPositif(self):
        """Méthode métier marquerFauxPositif() : passe le statut en FAUX_POSITIF."""
        self.statut = StatutVulnerabilite.FAUX_POSITIF
        self.save(update_fields=['statut'])
        self.audit.calculerScore()
        self.audit.save(update_fields=['scoreSecurite'])
        return self

    def marquerCorrigee(self):
        """Méthode métier marquerCorrigee() : passe le statut en CORRIGEE."""
        self.statut = StatutVulnerabilite.CORRIGEE
        self.save(update_fields=['statut'])
        self.audit.calculerScore()
        self.audit.save(update_fields=['scoreSecurite'])
        return self


class Preuve(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vulnerabilite = models.ForeignKey(
        Vulnerabilite,
        on_delete=models.CASCADE,
        related_name="preuves",
        verbose_name="Vulnérabilité associée"
    )
    type = models.CharField(max_length=50, default="HTTP_REQUEST", verbose_name="Type de preuve (ex: HTTP, Payload)")
    contenu = models.TextField(verbose_name="Contenu de la preuve / PoC")
    fichier = models.CharField(max_length=255, blank=True, default="", verbose_name="Chemin du fichier / Capture")
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Preuve (PoC)"
        verbose_name_plural = "Preuves (PoC)"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"Preuve PoC [{self.type}] pour {self.vulnerabilite.titre}"


class Recommandation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vulnerabilite = models.ForeignKey(
        Vulnerabilite,
        on_delete=models.CASCADE,
        related_name="recommandations",
        verbose_name="Vulnérabilité associée"
    )
    description = models.TextField(verbose_name="Description du correctif proposé")
    priorite = models.CharField(
        max_length=20,
        choices=Gravite.choices,
        default=Gravite.MOYENNE,
        verbose_name="Priorité d'application"
    )
    composantConcerne = models.CharField(max_length=255, blank=True, default="", verbose_name="Composant concerné")
    methodeValidation = models.TextField(blank=True, default="", verbose_name="Méthode de validation du patch")

    class Meta:
        verbose_name = "Recommandation"
        verbose_name_plural = "Recommandations"

    def __str__(self):
        return f"Recommandation [{self.priorite}] : {self.vulnerabilite.titre}"
