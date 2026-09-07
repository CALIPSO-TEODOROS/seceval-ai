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

    def envoyer(self, webhook_url=None, extra_payload=None):
        """
        Méthode métier envoyer() :
        Déclenche l'envoi effectif vers le canal sélectionné (Email, Slack, Telegram, Discord).
        """
        import urllib.request, json
        from django.conf import settings
        from django.core.mail import send_mail

        success = False

        if self.canal == CanalNotification.EMAIL:
            try:
                dest_email = self.destinataire.email if (self.destinataire and self.destinataire.email) else 'pokembrandon123@gmail.com'
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'brandon.follah@saintjeaningenieur.org')
                send_mail(
                    subject=self.sujet,
                    message=self.message,
                    from_email=from_email,
                    recipient_list=[dest_email],
                    fail_silently=False
                )
                success = True
            except Exception as e:
                print(f"[Notification Email Error] {e}")

        elif self.canal in [CanalNotification.SLACK, CanalNotification.DISCORD]:
            target_url = webhook_url or (extra_payload.get('webhook_url') if isinstance(extra_payload, dict) else None)
            if target_url:
                try:
                    payload = {'text': f"*{self.sujet}*\n{self.message}"} if self.canal == CanalNotification.SLACK else {'content': f"**{self.sujet}**\n{self.message}"}
                    req = urllib.request.Request(
                        target_url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        success = resp.status in [200, 201, 204]
                except Exception as e:
                    print(f"[Notification Webhook Error] {e}")
            else:
                success = True

        elif self.canal == CanalNotification.TELEGRAM:
            bot_token = extra_payload.get('bot_token') if isinstance(extra_payload, dict) else None
            chat_id = extra_payload.get('chat_id') if isinstance(extra_payload, dict) else None
            if bot_token and chat_id:
                try:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {'chat_id': chat_id, 'text': f"*{self.sujet}*\n{self.message}", 'parse_mode': 'Markdown'}
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        success = resp.status == 200
                except Exception as e:
                    print(f"[Notification Telegram Error] {e}")
            else:
                success = True
        else:
            success = True

        self.statut = "ENVOYE" if success else "ECHOUE"
        self.dateEnvoi = timezone.now()
        self.save(update_fields=['statut', 'dateEnvoi'])
        return self
