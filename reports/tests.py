import json
import uuid
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from reports.models import Rapport, FormatRapport, StatutRapport
from vulns.models import Vulnerabilite, Gravite
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible, TypeCible


class ReportModelTests(TestCase):

    def setUp(self):
        self.projet = Projet.creer(nom="Projet Report Test", organisation="Report Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://report-test.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)
        self.vuln = Vulnerabilite.objects.create(
            audit=self.audit,
            titre="XSS in Report Test",
            description="Test XSS",
            gravite=Gravite.ELEVEE,
            scoreCVSS=7.5
        )

    def test_rapport_creation_and_generer(self):
        r = Rapport.objects.create(
            audit=self.audit,
            titre="Rapport de Test Automatisé",
            format=FormatRapport.JSON
        )
        self.assertIsInstance(r.id, uuid.UUID)
        self.assertEqual(r.statut, StatutRapport.BROUILLON)

        r.generer()
        r.refresh_from_db()
        self.assertEqual(r.statut, StatutRapport.EN_REVISION)
        self.assertTrue(os.path.exists(r.cheminFichier))
        self.assertGreaterEqual(r.vulnerabilites.count(), 1)

    def test_rapport_lifecycle_methods(self):
        r = Rapport.objects.create(
            audit=self.audit,
            titre="Rapport Lifecycle Test",
            format=FormatRapport.HTML
        )
        r.generer()

        r.valider()
        self.assertEqual(r.statut, StatutRapport.VALIDE)

        r.publier()
        self.assertEqual(r.statut, StatutRapport.PUBLIE)

        content = r.telecharger()
        self.assertIn("Rapport Lifecycle Test", content)


class ReportAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.projet = Projet.creer(nom="Projet Report API", organisation="Report API Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://api-report.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)
        self.rapport = Rapport.objects.create(
            audit=self.audit,
            titre="Rapport API Test",
            format=FormatRapport.HTML
        )
        self.rapport.generer()

    def test_reports_list_and_create_api(self):
        res = self.client.get(reverse('reports:list-create'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data['total'], 1)

        # Create Report
        res_create = self.client.post(
            reverse('reports:list-create'),
            data=json.dumps({
                'audit_id': str(self.audit.id),
                'titre': 'Nouveau Rapport JSON',
                'format': FormatRapport.JSON
            }),
            content_type='application/json'
        )
        self.assertEqual(res_create.status_code, 201)

    def test_report_detail_and_lifecycle_api(self):
        # Detail
        res_det = self.client.get(reverse('reports:detail', kwargs={'report_id': self.rapport.id}))
        self.assertEqual(res_det.status_code, 200)

        # Valider
        self.client.post(reverse('reports:valider', kwargs={'report_id': self.rapport.id}))
        self.rapport.refresh_from_db()
        self.assertEqual(self.rapport.statut, StatutRapport.VALIDE)

        # Publier
        self.client.post(reverse('reports:publier', kwargs={'report_id': self.rapport.id}))
        self.rapport.refresh_from_db()
        self.assertEqual(self.rapport.statut, StatutRapport.PUBLIE)

        # Telecharger
        res_dl = self.client.get(reverse('reports:telecharger', kwargs={'report_id': self.rapport.id}))
        self.assertEqual(res_dl.status_code, 200)

    def test_seed_reports_command(self):
        call_command('seed_reports')
        self.assertTrue(Rapport.objects.filter(format=FormatRapport.HTML).exists())
        self.assertTrue(Rapport.objects.filter(format=FormatRapport.JSON).exists())
