import uuid
from django.db import models
from django.utils import timezone
from audits.models import Audit
from users.models import Utilisateur


class CanalNotification(models.TextChoices):
    EMAIL = 'EMAIL', 'Email'
    SLACK = 'SLACK', 'Slack Webhook'
    TELEGRAM = 'TELEGRAM', 'Telegram Bot'
    DISCORD = 'DISCORD', 'Discord Webhook'


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="Audit associé"
    )
    destinataire = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Utilisateur destinataire"
    )
    canal = models.CharField(
        max_length=20,
        choices=CanalNotification.choices,
        default=CanalNotification.EMAIL,
        verbose_name="Canal de notification"
    )
    sujet = models.CharField(max_length=255, verbose_name="Sujet / Titre")
    message = models.TextField(verbose_name="Contenu du message")
    statut = models.CharField(
        max_length=20,
        default="EN_ATTENTE",
        verbose_name="Statut de l'envoi"
    )
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    dateEnvoi = models.DateTimeField(null=True, blank=True, verbose_name="Date d'envoi effectif")

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"Notification [{self.canal}] à {self.destinataire.email} - {self.sujet} ({self.statut})"

    def envoyer(self):
        """
        Méthode métier envoyer() :
        Déclenche l'envoi selon le canal (Email, Slack, Telegram, Discord),
        met à jour le statut en 'ENVOYE' et renseigne dateEnvoi.
        """
        # Simulation d'envoi vers le canal configuré
        self.statut = "ENVOYE"
        self.dateEnvoi = timezone.now()
        self.save(update_fields=['statut', 'dateEnvoi'])
        return self
