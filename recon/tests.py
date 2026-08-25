import json
import uuid
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from recon.models import TechnologieDetectee, ServiceDetecte, CertificatSSL
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible, TypeCible
from users.models import Utilisateur


class ReconModelTests(TestCase):

    def setUp(self):
        self.projet = Projet.creer(nom="Projet Recon Test", organisation="Recon Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://recon-test.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)

    def test_technologie_creation(self):
        tech = TechnologieDetectee.objects.create(
            audit=self.audit,
            nom="Django",
            version="5.0.2",
            categorie="Web Framework",
            niveauConfiance=99.0
        )
        self.assertIsInstance(tech.id, uuid.UUID)
        self.assertEqual(tech.nom, "Django")
        self.assertIn("Django v5.0.2", str(tech))

    def test_service_creation(self):
        srv = ServiceDetecte.objects.create(
            audit=self.audit,
            port=443,
            protocole="tcp",
            service="https",
            version="Nginx 1.24.0",
            etat="open"
        )
        self.assertEqual(srv.port, 443)
        self.assertIn("Port 443/tcp", str(srv))

    def test_certificat_ssl_creation(self):
        today = datetime.date.today()
        cert = CertificatSSL.objects.create(
            audit=self.audit,
            sujet="CN=recon-test.io",
            emetteur="Let's Encrypt Authority X3",
            dateDebut=today,
            dateExpiration=today + datetime.timedelta(days=90),
            valide=True,
            protocole="TLSv1.3"
        )
        self.assertTrue(cert.valide)
        self.assertIn("recon-test.io", str(cert))


class ReconAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.projet = Projet.creer(nom="Projet Recon API Test", organisation="API Recon Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://api-recon.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)

    def test_audit_recon_results_api(self):
        url = reverse('recon:audit-results', kwargs={'audit_id': self.audit.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['summary']['total_technologies'], 0)

    def test_scan_simulation_api(self):
        scan_url = reverse('recon:audit-scan', kwargs={'audit_id': self.audit.id})
        res = self.client.post(scan_url)
        self.assertEqual(res.status_code, 200)

        # Check results now exist
        results_url = reverse('recon:audit-results', kwargs={'audit_id': self.audit.id})
        res_results = self.client.get(results_url)
        data = res_results.json()
        self.assertGreater(data['summary']['total_technologies'], 0)
        self.assertGreater(data['summary']['total_services'], 0)
        self.assertGreater(data['summary']['total_certificats'], 0)

    def test_manual_creations_api(self):
        # Create Tech
        res_tech = self.client.post(
            reverse('recon:create-technologie'),
            data=json.dumps({
                'audit_id': str(self.audit.id),
                'nom': 'Vue.js',
                'version': '3.4.0',
                'categorie': 'Frontend Framework'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_tech.status_code, 201)

        # Create Service
        res_srv = self.client.post(
            reverse('recon:create-service'),
            data=json.dumps({
                'audit_id': str(self.audit.id),
                'port': 8080,
                'service': 'http-alt'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_srv.status_code, 201)

    def test_seed_recon_command(self):
        call_command('seed_recon')
        self.assertTrue(TechnologieDetectee.objects.exists())
        self.assertTrue(ServiceDetecte.objects.exists())
        self.assertTrue(CertificatSSL.objects.exists())
