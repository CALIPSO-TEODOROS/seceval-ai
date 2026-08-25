import uuid
from django.db import models
from users.models import Utilisateur
from projects.models import Projet
from audits.models import Audit


class JournalActivite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="journaux_activite",
        verbose_name="Utilisateur initiateur"
    )
    projet = models.ForeignKey(
        Projet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journaux_activite",
        verbose_name="Projet concerné"
    )
    audit = models.ForeignKey(
        Audit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journaux_activite",
        verbose_name="Audit concerné"
    )
    action = models.CharField(max_length=255, verbose_name="Action effectuée")
    ressource = models.CharField(max_length=255, verbose_name="Ressource ciblée")
    details = models.TextField(blank=True, default="", verbose_name="Détails techniques")
    adresseIP = models.CharField(max_length=45, default="127.0.0.1", verbose_name="Adresse IP")
    dateAction = models.DateTimeField(auto_now_add=True, verbose_name="Date de l'action")

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journaux d'activité"
        ordering = ['-dateAction']

    def __str__(self):
        return f"[{self.dateAction.strftime('%Y-%m-%d %H:%M')}] {self.utilisateur.nom} - {self.action} ({self.ressource})"

    @classmethod
    def enregistrer(cls, utilisateur, action, ressource, details="", adresseIP="127.0.0.1", projet=None, audit=None):
        """
        Méthode statique/helper métier pour enregistrer un événement d'activité.
        """
        return cls.objects.create(
            utilisateur=utilisateur,
            projet=projet,
            audit=audit,
            action=action,
            ressource=ressource,
            details=details,
            adresseIP=adresseIP
        )
