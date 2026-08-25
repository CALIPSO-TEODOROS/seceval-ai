import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from notifications_app.models import Notification, CanalNotification
from audits.models import Audit, TypeAudit
from users.models import Utilisateur
from projects.models import Projet, Cible, TypeCible


class NotificationModelTests(TestCase):

    def setUp(self):
        self.user = Utilisateur.objects.create_user(email="notif-user@test.io", nom="Notif User", password="Password123!")
        self.projet = Projet.creer(nom="Projet Notif Test", organisation="Notif Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://notif-test.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)

    def test_notification_creation_and_envoyer(self):
        n = Notification.objects.create(
            destinataire=self.user,
            audit=self.audit,
            canal=CanalNotification.SLACK,
            sujet="Test Notification Slack",
            message="Contenu de test pour Slack"
        )
        self.assertIsInstance(n.id, uuid.UUID)
        self.assertEqual(n.statut, "EN_ATTENTE")

        n.envoyer()
        n.refresh_from_db()
        self.assertEqual(n.statut, "ENVOYE")
        self.assertIsNotNone(n.dateEnvoi)


class NotificationAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = Utilisateur.objects.create_user(email="api-notif@test.io", nom="API Notif User", password="Password123!")
        self.projet = Projet.creer(nom="Projet API Notif", organisation="API Notif Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://api-notif.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)
        self.notif = Notification.objects.create(
            destinataire=self.user,
            audit=self.audit,
            canal=CanalNotification.EMAIL,
            sujet="Alerte Sécurité Email",
            message="Message de test d'alerte"
        )

    def test_notifications_list_and_create_api(self):
        res = self.client.get(reverse('notifications_app:list-create'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data['total'], 1)

        # Create & Send Notification
        res_create = self.client.post(
            reverse('notifications_app:list-create'),
            data=json.dumps({
                'destinataire_id': str(self.user.id),
                'audit_id': str(self.audit.id),
                'canal': CanalNotification.DISCORD,
                'sujet': 'Message Discord automatique',
                'message': 'Audit terminé avec un score de 95/100'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_create.status_code, 201)

    def test_notification_detail_and_envoyer_api(self):
        # Detail
        res_det = self.client.get(reverse('notifications_app:detail', kwargs={'notification_id': self.notif.id}))
        self.assertEqual(res_det.status_code, 200)

        # Envoyer Action
        res_send = self.client.post(reverse('notifications_app:envoyer', kwargs={'notification_id': self.notif.id}))
        self.assertEqual(res_send.status_code, 200)
        self.notif.refresh_from_db()
        self.assertEqual(self.notif.statut, "ENVOYE")

    def test_seed_notifications_command(self):
        call_command('seed_notifications')
        self.assertTrue(Notification.objects.filter(canal=CanalNotification.EMAIL).exists())
        self.assertTrue(Notification.objects.filter(canal=CanalNotification.SLACK).exists())
