import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from logs_app.models import JournalActivite
from audits.models import Audit, TypeAudit
from users.models import Utilisateur
from projects.models import Projet, Cible, TypeCible


class JournalModelTests(TestCase):

    def setUp(self):
        self.user = Utilisateur.objects.create_user(email="log-user@test.io", nom="Log User", password="Password123!")
        self.projet = Projet.creer(nom="Projet Log Test", organisation="Log Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://log-test.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)

    def test_journal_creation_and_enregistrer(self):
        log = JournalActivite.enregistrer(
            utilisateur=self.user,
            action="TEST_ACTION",
            ressource="Test Resource",
            details="Details test",
            adresseIP="127.0.0.1",
            projet=self.projet,
            audit=self.audit
        )
        self.assertIsInstance(log.id, uuid.UUID)
        self.assertEqual(log.action, "TEST_ACTION")
        self.assertEqual(log.utilisateur, self.user)
        self.assertEqual(log.projet, self.projet)
        self.assertEqual(log.audit, self.audit)


class JournalAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = Utilisateur.objects.create_user(email="api-log@test.io", nom="API Log User", password="Password123!")
        self.projet = Projet.creer(nom="Projet API Log", organisation="API Log Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://api-log-target.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)
        self.log = JournalActivite.enregistrer(
            utilisateur=self.user,
            action="CONNEXION",
            ressource="Portail Web",
            details="Authentification réussie",
            projet=self.projet,
            audit=self.audit
        )

    def test_logs_list_and_create_api(self):
        res = self.client.get(reverse('logs_app:list-create'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data['total'], 1)

        # Create Log via API
        res_create = self.client.post(
            reverse('logs_app:list-create'),
            data=json.dumps({
                'utilisateur_id': str(self.user.id),
                'projet_id': str(self.projet.id),
                'action': 'EXPORT_RAPPORT',
                'ressource': 'Rapport PDF',
                'details': 'Téléchargement du fichier de rapport'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_create.status_code, 201)

    def test_log_detail_api(self):
        res_det = self.client.get(reverse('logs_app:detail', kwargs={'log_id': self.log.id}))
        self.assertEqual(res_det.status_code, 200)
        data = res_det.json()
        self.assertEqual(data['action'], 'CONNEXION')

    def test_seed_logs_command(self):
        call_command('seed_logs')
        self.assertTrue(JournalActivite.objects.filter(action='CONNEXION_UTILISATEUR').exists())
