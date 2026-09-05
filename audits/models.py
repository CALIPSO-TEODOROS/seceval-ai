import uuid
import json
import urllib.request
import urllib.parse
from django.db import models

from django.utils import timezone
from projects.models import Projet, Cible
from users.models import Utilisateur



class TypeAudit(models.TextChoices):
    LEGER = 'LEGER', 'Léger (Reconnaissance rapide)'
    STANDARD = 'STANDARD', 'Standard (OWASP Top 10)'
    APPROFONDI = 'APPROFONDI', 'Approfondi (Pentest complet)'
    API = 'API', 'API REST & GraphQL'
    SSL_TLS = 'SSL_TLS', 'Analyse SSL / TLS & Chiffrement'
    CONFIGURATION = 'CONFIGURATION', 'Audit de Configuration & Headers'


class StatutAudit(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    PLANIFICATION = 'PLANIFICATION', 'Planification'
    EN_COURS = 'EN_COURS', 'En cours'
    TERMINE = 'TERMINE', 'Terminé'
    PARTIEL = 'PARTIEL', 'Terminé partiellement'
    ECHOUE = 'ECHOUE', 'Échoué'
    ANNULE = 'ANNULE', 'Annulé'


class StatutExecution(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    RUNNING = 'RUNNING', 'En cours d\'exécution'
    COMPLETED = 'COMPLETED', 'Terminé avec succès'
    FAILED = 'FAILED', 'Échoué'
    CANCELLED = 'CANCELLED', 'Annulé'
    TIMEOUT = 'TIMEOUT', 'Dépassement de temps'


class TypePlanification(models.TextChoices):
    UNIQUE = 'UNIQUE', 'Planification Unique (Ponctuelle)'
    REPETITIVE = 'REPETITIVE', 'Planification Répétitive (Récurrente)'


class FrequenceAudit(models.TextChoices):
    AUCUNE = 'AUCUNE', 'Aucune récurrence'
    QUOTIDIEN = 'QUOTIDIEN', 'Quotidien (Toutes les 24h)'
    HEBDOMADAIRE = 'HEBDOMADAIRE', 'Hebdomadaire (Toutes les semaines)'
    MENSUEL = 'MENSUEL', 'Mensuel (Tous les mois)'


class Audit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Titre de l'audit"
    )
    contexte = models.TextField(
        blank=True,
        default="",
        verbose_name="Description du contexte de l'audit"
    )
    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name="audits",
        verbose_name="Projet"
    )
    cible = models.ForeignKey(
        Cible,
        on_delete=models.CASCADE,
        related_name="audits",
        verbose_name="Cible"
    )
    lancePar = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits_lances",
        verbose_name="Lancé par"
    )
    type = models.CharField(
        max_length=30,
        choices=TypeAudit.choices,
        default=TypeAudit.STANDARD,
        verbose_name="Type d'audit"
    )
    statut = models.CharField(
        max_length=30,
        choices=StatutAudit.choices,
        default=StatutAudit.EN_ATTENTE,
        verbose_name="Statut de l'audit"
    )
    typePlanification = models.CharField(
        max_length=20,
        choices=TypePlanification.choices,
        default=TypePlanification.UNIQUE,
        verbose_name="Type de planification"
    )
    frequence = models.CharField(
        max_length=20,
        choices=FrequenceAudit.choices,
        default=FrequenceAudit.AUCUNE,
        verbose_name="Fréquence de récurrence"
    )
    heureExecution = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure d'exécution programmée"
    )
    prochaineExecution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Prochaine exécution"
    )
    webhookN8nUrl = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="URL Trigger Webhook n8n"
    )
    emailsNotification = models.TextField(
        blank=True,
        default="",
        verbose_name="Adresses email de notification (séparées par des virgules)"
    )
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    dateDebut = models.DateTimeField(null=True, blank=True, verbose_name="Date de début")
    dateDernierLancement = models.DateTimeField(null=True, blank=True, verbose_name="Date du dernier lancement")
    dateFin = models.DateTimeField(null=True, blank=True, verbose_name="Date de fin")
    scoreSecurite = models.FloatField(default=0.0, verbose_name="Score de sécurité (0 à 100)")
    progression = models.IntegerField(default=0, verbose_name="Progression (0 à 100%)")
    resultatBrutN8n = models.JSONField(default=dict, blank=True, null=True, verbose_name="Résultats bruts reçus de n8n")

    class Meta:

        verbose_name = "Audit de Sécurité"
        verbose_name_plural = "Audits de Sécurité"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"Audit {self.get_type_display()} - {self.cible.valeur} [{self.get_statut_display()}]"

    def declencherWebhookN8n(self):
        """
        Méthode métier declencherWebhookN8n() :
        Construit un prompt unifié structuré pour l'Agent IA n8n et l'envoie via HTTP GET.
        """
        if not self.webhookN8nUrl:
            return False

        type_display = self.get_type_display()
        heure_str = self.heureExecution.strftime('%H:%M:%S') if self.heureExecution else 'Immédiat'
        contexte_text = self.contexte if self.contexte else 'Aucun contexte spécifique renseigné.'

        # Formater un prompt unifié prêt à l'emploi pour le LLM / Agent IA n8n
        prompt_ia = (
            f"[DIRECTIVE AUDIT SECURITE IA]\n"
            f"ID Audit: {self.id}\n"
            f"Titre de l'Audit: {self.titre or f'Audit {type_display} - {self.cible.valeur}'}\n"
            f"Type d'Audit: {type_display}\n"
            f"Cible d'Évaluation: {self.cible.valeur} ({self.cible.type})\n"
            f"Projet Associé: {self.projet.nom} ({self.projet.organisation})\n"
            f"Type de Planification: {self.get_typePlanification_display()} (Fréquence: {self.get_frequence_display()})\n"
            f"Heure d'Exécution Programmée: {heure_str}\n"
            f"Horodatage de Déclenchement: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"--- DESCRIPTION DU CONTEXTE & OBJECTIFS METIERS ---\n"
            f"{contexte_text}\n\n"
            f"INSTRUCTION AGENT IA: Veuillez analyser les objectifs métiers et exécuter les étapes du scan de sécurité d'après les directives ci-dessus."
        )

        query_params = {
            'prompt': prompt_ia,
            'contexte': contexte_text,
            'titre': self.titre or f"Audit {type_display} - {self.cible.valeur}",
            'cible': self.cible.valeur,
            'projet': self.projet.nom,
            'type': self.type,
            'audit_id': str(self.id)
        }


        try:
            query_string = urllib.parse.urlencode(query_params)
            sep = '&' if '?' in self.webhookN8nUrl else '?'
            full_url = f"{self.webhookN8nUrl}{sep}{query_string}"

            req = urllib.request.Request(
                full_url,
                headers={'User-Agent': 'SecEvalAI-Webhook/1.0'},
                method='GET'
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in [200, 201, 202, 204]
        except Exception as e:
            print(f"[Webhook n8n Warning] Impossible de contacter {self.webhookN8nUrl}: {e}")
            return False



    def demarrer(self):
        """
        Méthode métier demarrer() :
        Met le statut à EN_COURS, enregistre dateDebut et dateDernierLancement, déclenche le webhook n8n si présent,
        et initialise le plan d'audit s'il n'existe pas.
        """
        now = timezone.now()
        self.statut = StatutAudit.EN_COURS
        self.dateDernierLancement = now
        if not self.dateDebut:
            self.dateDebut = now
        self.save(update_fields=['statut', 'dateDebut', 'dateDernierLancement'])

        # Enregistrer une nouvelle exécution d'audit dans l'historique
        ExecutionAudit.objects.create(
            audit=self,
            statut=StatutAudit.EN_COURS
        )

        # Déclenchement du Webhook n8n

        if self.webhookN8nUrl:
            self.declencherWebhookN8n()

        # Initialiser le PlanAudit et les étapes par défaut si absent
        if not hasattr(self, 'plan'):
            plan = PlanAudit.objects.create(
                audit=self,
                description=f"Plan d'évaluation {self.get_type_display()} généré automatiquement par l'agent IA."
            )
            self._generer_etapes_par_defaut(plan)

        return self



    def mettreEnPause(self):
        """Méthode métier mettreEnPause() : passe le statut en PLANIFICATION."""
        self.statut = StatutAudit.PLANIFICATION
        self.save(update_fields=['statut'])
        return self

    def arreter(self):
        """Méthode métier arreter() : annule l'audit."""
        self.statut = StatutAudit.ANNULE
        self.dateFin = timezone.now()
        self.save(update_fields=['statut', 'dateFin'])
        return self

    def terminer(self):
        """
        Méthode métier terminer() :
        Marque l'audit comme TERMINE, met la progression à 100%, définit dateFin et calcule le score.
        """
        self.statut = StatutAudit.TERMINE
        self.dateFin = timezone.now()
        self.progression = 100
        self.calculerScore()
        self.save(update_fields=['statut', 'dateFin', 'progression', 'scoreSecurite'])
        return self

    def calculerScore(self):
        """
        Méthode métier calculerScore() :
        Calcule le score de sécurité (Float sur 100) basé sur les étapes réussies de l'audit.
        """
        if hasattr(self, 'plan') and self.plan.etapes.exists():
            etapes = self.plan.etapes.all()
            completed = etapes.filter(statut=StatutExecution.COMPLETED).count()
            total = etapes.count()

            if total > 0:
                raw_score = (completed / total) * 100.0
                self.scoreSecurite = round(max(0.0, min(100.0, raw_score)), 1)
            else:
                self.scoreSecurite = 100.0
        else:
            self.scoreSecurite = 100.0

        return self.scoreSecurite

    def _generer_etapes_par_defaut(self, plan):
        """Génère les étapes canoniques de l'audit selon son type."""
        etapes_noms = [
            "Reconnaissance et empreinte numérique",
            "Analyse des en-têtes de sécurité et SSL/TLS",
            "Détection des vulnérabilités d'authentification",
            "Analyse des injections (SQLi, XSS, CSRF)",
            "Génération du rapport et scoring de sécurité"
        ]

        if self.type == TypeAudit.API:
            etapes_noms = [
                "Inspection du schéma API (OpenAPI/GraphQL)",
                "Test d'authentification et JWT",
                "Contrôle d'accès et autorisation d'objets (BOLA)",
                "Test de limitation de débit (Rate Limiting)",
                "Validation des entrées et sérialisation"
            ]
        elif self.type == TypeAudit.SSL_TLS:
            etapes_noms = [
                "Vérification de la chaîne de certificat",
                "Analyse des ciphers et protocoles supportés",
                "Détection des failles SSL connues (Heartbleed, POODLE)",
                "Vérification HSTS et validation DNSSEC"
            ]

        for i, nom_etape in enumerate(etapes_noms, start=1):
            plan.ajouterEtape(nom=nom_etape, ordre=i)


class PlanAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.OneToOneField(
        Audit,
        on_delete=models.CASCADE,
        related_name="plan",
        verbose_name="Audit"
    )
    description = models.TextField(blank=True, default="", verbose_name="Description du plan")
    dateGeneration = models.DateTimeField(auto_now_add=True, verbose_name="Date de génération")

    class Meta:
        verbose_name = "Plan d'Audit"
        verbose_name_plural = "Plans d'Audit"

    def __str__(self):
        return f"Plan pour Audit {self.audit.id}"

    def ajouterEtape(self, nom, ordre=None):
        """
        Méthode métier ajouterEtape() :
        Ajoute une nouvelle EtapeAudit au plan.
        """
        if ordre is None:
            ordre = self.etapes.count() + 1
        etape = EtapeAudit.objects.create(
            plan=self,
            nom=nom,
            ordre=ordre,
            statut=StatutExecution.PENDING
        )
        return etape

    def reordonnerEtapes(self):
        """
        Méthode métier reordonnerEtapes() :
        Réindexe les étapes de 1 à N selon leur ordre actuel.
        """
        etapes = self.etapes.order_by('ordre', 'id')
        for index, etape in enumerate(etapes, start=1):
            if etape.ordre != index:
                etape.ordre = index
                etape.save(update_fields=['ordre'])
        return etapes


class EtapeAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        PlanAudit,
        on_delete=models.CASCADE,
        related_name="etapes",
        verbose_name="Plan d'audit"
    )
    ordre = models.IntegerField(default=1, verbose_name="Ordre de l'étape")
    nom = models.CharField(max_length=255, verbose_name="Nom de l'étape")
    statut = models.CharField(
        max_length=20,
        choices=StatutExecution.choices,
        default=StatutExecution.PENDING,
        verbose_name="Statut d'exécution"
    )
    dateDebut = models.DateTimeField(null=True, blank=True, verbose_name="Date de début")
    dateFin = models.DateTimeField(null=True, blank=True, verbose_name="Date de fin")

    class Meta:
        verbose_name = "Étape d'Audit"
        verbose_name_plural = "Étapes d'Audit"
        ordering = ['ordre']

    def __str__(self):
        return f"Étape {self.ordre}: {self.nom} [{self.get_statut_display()}]"


class ExecutionAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name="Audit parent"
    )
    dateExecution = models.DateTimeField(auto_now_add=True, verbose_name="Date & Heure d'exécution")
    dateFin = models.DateTimeField(null=True, blank=True, verbose_name="Date & Heure de fin")
    statut = models.CharField(
        max_length=20,
        choices=StatutAudit.choices,
        default=StatutAudit.EN_COURS,
        verbose_name="Statut de l'exécution"
    )
    scoreSecurite = models.FloatField(default=0.0, verbose_name="Score de sécurité (0 à 100)")
    resultatBrutN8n = models.JSONField(default=dict, blank=True, null=True, verbose_name="Résultats bruts n8n")
    rapportText = models.TextField(blank=True, default="", verbose_name="Rapport d'analyse texte")

    class Meta:
        verbose_name = "Exécution d'Audit"
        verbose_name_plural = "Exécutions d'Audit"
        ordering = ['-dateExecution']

    def __str__(self):
        return f"Exécution {self.audit.titre} - {self.dateExecution.strftime('%Y-%m-%d %H:%M:%S')} [{self.get_statut_display()}]"

