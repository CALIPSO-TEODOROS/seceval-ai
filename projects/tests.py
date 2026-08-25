import json
import datetime
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from projects.models import (
    Projet,
    Cible,
    AutorisationCible,
    StatutProjet,
    TypeCible,
    Environnement,
    StatutCible
)


class ProjectManagementModelTests(TestCase):

    def setUp(self):
        self.project = Projet.creer(
            nom="Projet Test Sécurité",
            organisation="Org Test",
            description="Description du projet test",
            statut=StatutProjet.ACTIF
        )

    def test_projet_creation_and_methods(self):
        self.assertIsInstance(self.project.id, uuid.UUID)
        self.assertEqual(self.project.nom, "Projet Test Sécurité")
        self.assertEqual(self.project.statut, StatutProjet.ACTIF)
        self.assertIn("Projet Test Sécurité", str(self.project))

        # Test modifier()
        self.project.modifier(nom="Projet Modifié", description="Nouvelle desc")
        self.project.refresh_from_db()
        self.assertEqual(self.project.nom, "Projet Modifié")
        self.assertEqual(self.project.description, "Nouvelle desc")

        # Test archiver()
        self.project.archiver()
        self.project.refresh_from_db()
        self.assertEqual(self.project.statut, StatutProjet.ARCHIVE)
        self.assertIsNotNone(self.project.dateArchivage)

    def test_cible_accessibilite(self):
        cible_url = Cible.objects.create(
            projet=self.project,
            valeur="https://sec-target.io",
            type=TypeCible.URL,
            environnement=Environnement.TEST
        )
        accessible, msg = cible_url.verifierAccessibilite()
        self.assertTrue(accessible)
        self.assertIn("URL valide", msg)

        cible_bad_url = Cible.objects.create(
            projet=self.project,
            valeur="ftp://invalid-url.io",
            type=TypeCible.URL,
            environnement=Environnement.TEST
        )
        accessible, msg = cible_bad_url.verifierAccessibilite()
        self.assertFalse(accessible)

        cible_ip = Cible.objects.create(
            projet=self.project,
            valeur="10.0.0.1",
            type=TypeCible.ADRESSE_IP,
            environnement=Environnement.DEVELOPPEMENT
        )
        accessible_ip, _ = cible_ip.verifierAccessibilite()
        self.assertTrue(accessible_ip)

    def test_autorisation_cible_valide(self):
        cible = Cible.objects.create(
            projet=self.project,
            valeur="https://app.target.io",
            type=TypeCible.URL,
            environnement=Environnement.PREPRODUCTION
        )

        today = timezone.now().date()
        auth_valide = AutorisationCible.objects.create(
            cible=cible,
            dateDebut=today - datetime.timedelta(days=10),
            dateFin=today + datetime.timedelta(days=10),
            preuve="PREUVE-001.pdf",
            testsActifsAutorises=True
        )

        self.assertTrue(auth_valide.estValide())
        auth_ok, msg = cible.verifierAutorisation()
        self.assertTrue(auth_ok)
        self.assertEqual(cible.statut, StatutCible.AUTORISEE)

    def test_autorisation_cible_expiree(self):
        cible = Cible.objects.create(
            projet=self.project,
            valeur="https://expired.target.io",
            type=TypeCible.URL,
            environnement=Environnement.TEST
        )

        today = timezone.now().date()
        auth_expiree = AutorisationCible.objects.create(
            cible=cible,
            dateDebut=today - datetime.timedelta(days=30),
            dateFin=today - datetime.timedelta(days=1),
            preuve="PREUVE-EXPIRED.pdf"
        )

        self.assertFalse(auth_expiree.estValide())
        auth_ok, msg = cible.verifierAutorisation()
        self.assertFalse(auth_ok)
        self.assertNotEqual(cible.statut, StatutCible.AUTORISEE)


class ProjectAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.project = Projet.creer(
            nom="API Project Test",
            organisation="API Org",
            description="API Description"
        )

    def test_projects_list_and_create_api(self):
        # GET List
        response = self.client.get(reverse('projects:list-create'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data['total'], 1)

        # POST Create
        create_resp = self.client.post(
            reverse('projects:list-create'),
            data=json.dumps({
                'nom': 'Nouveau Projet API',
                'organisation': 'New Org',
                'description': 'Desc'
            }),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 201)
        self.assertTrue(Projet.objects.filter(nom='Nouveau Projet API').exists())

    def test_project_detail_update_archive_api(self):
        detail_url = reverse('projects:detail', kwargs={'project_id': self.project.id})

        # GET Detail
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, 200)

        # PATCH Update
        patch_res = self.client.patch(
            detail_url,
            data=json.dumps({'nom': 'API Project Renamed'}),
            content_type='application/json'
        )
        self.assertEqual(patch_res.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.nom, 'API Project Renamed')

        # POST Archive
        archive_url = reverse('projects:archive', kwargs={'project_id': self.project.id})
        arch_res = self.client.post(archive_url)
        self.assertEqual(arch_res.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.statut, StatutProjet.ARCHIVE)

    def test_cible_and_authorization_api(self):
        cibles_url = reverse('projects:cibles', kwargs={'project_id': self.project.id})

        # POST Add Cible
        res_cible = self.client.post(
            cibles_url,
            data=json.dumps({
                'valeur': 'https://api.target.org',
                'type': TypeCible.API_REST,
                'environnement': Environnement.TEST
            }),
            content_type='application/json'
        )
        self.assertEqual(res_cible.status_code, 201)
        cible_id = res_cible.json()['cible']['id']

        # POST Add Authorization
        today = timezone.now().date()
        auth_url = reverse('projects:cible-authorizations', kwargs={'cible_id': cible_id})
        res_auth = self.client.post(
            auth_url,
            data=json.dumps({
                'dateDebut': str(today),
                'dateFin': str(today + datetime.timedelta(days=100)),
                'preuve': 'DOC-AUTH-101',
                'testsActifsAutorises': True
            }),
            content_type='application/json'
        )
        self.assertEqual(res_auth.status_code, 201)

        # POST Verify Cible
        verify_url = reverse('projects:verify-cible', kwargs={'cible_id': cible_id})
        res_verify = self.client.post(verify_url)
        self.assertEqual(res_verify.status_code, 200)
        self.assertTrue(res_verify.json()['accessibilite']['valide'])

    def test_seed_projects_command(self):
        call_command('seed_projects')
        self.assertTrue(Projet.objects.filter(nom="Evaluation Banque En Ligne").exists())
        self.assertTrue(Cible.objects.filter(valeur="https://app.fintechcorp.io").exists())
