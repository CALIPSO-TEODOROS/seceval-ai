import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from vulns.models import Vulnerabilite, Preuve, Recommandation, Gravite, StatutVulnerabilite
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible, TypeCible


class VulnModelTests(TestCase):

    def setUp(self):
        self.projet = Projet.creer(nom="Projet Vuln Test", organisation="Vuln Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://vuln-test.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)

    def test_vulnerabilite_creation(self):
        v = Vulnerabilite.objects.create(
            audit=self.audit,
            titre="XSS Test",
            description="Test XSS vulnerability",
            gravite=Gravite.ELEVEE,
            scoreCVSS=7.5,
            codeCWE="CWE-79"
        )
        self.assertIsInstance(v.id, uuid.UUID)
        self.assertEqual(v.statut, StatutVulnerabilite.NOUVELLE)

    def test_vulnerabilite_lifecycle_methods(self):
        v = Vulnerabilite.objects.create(
            audit=self.audit,
            titre="SQL Injection",
            description="Test SQLi",
            gravite=Gravite.CRITIQUE,
            scoreCVSS=9.8,
            codeCWE="CWE-89"
        )

        # Confirmer
        v.confirmer()
        v.refresh_from_db()
        self.assertEqual(v.statut, StatutVulnerabilite.CONFIRMEE)

        # Faux positif
        v.marquerFauxPositif()
        v.refresh_from_db()
        self.assertEqual(v.statut, StatutVulnerabilite.FAUX_POSITIF)

        # Corrigée
        v.marquerCorrigee()
        v.refresh_from_db()
        self.assertEqual(v.statut, StatutVulnerabilite.CORRIGEE)

        # Classifier
        v.classifier(gravite=Gravite.MOYENNE, scoreCVSS=5.0, codeCWE="CWE-200")
        v.refresh_from_db()
        self.assertEqual(v.gravite, Gravite.MOYENNE)
        self.assertEqual(v.scoreCVSS, 5.0)
        self.assertEqual(v.codeCWE, "CWE-200")

    def test_preuve_and_recommandation_creation(self):
        v = Vulnerabilite.objects.create(
            audit=self.audit,
            titre="Weak Password Policy",
            description="Description test"
        )
        preuve = Preuve.objects.create(
            vulnerabilite=v,
            type="PAYLOAD",
            contenu="password=123"
        )
        rec = Recommandation.objects.create(
            vulnerabilite=v,
            description="Fix password rules",
            priorite=Gravite.ELEVEE,
            composantConcerne="Auth Module"
        )
        self.assertEqual(v.preuves.count(), 1)
        self.assertEqual(v.recommandations.count(), 1)


class VulnAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.projet = Projet.creer(nom="Projet Vuln API", organisation="Vuln API Org")
        self.cible = Cible.objects.create(projet=self.projet, valeur="https://api-vuln.io", type=TypeCible.URL)
        self.audit = Audit.objects.create(projet=self.projet, cible=self.cible, type=TypeAudit.STANDARD)
        self.vuln = Vulnerabilite.objects.create(
            audit=self.audit,
            titre="XSS API Test",
            description="Description XSS",
            gravite=Gravite.MOYENNE,
            scoreCVSS=6.1,
            codeCWE="CWE-79"
        )

    def test_vulns_list_and_create_api(self):
        res = self.client.get(reverse('vulns:list-create'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data['total'], 1)

        # Create vuln manually should return 403 Forbidden
        res_create = self.client.post(
            reverse('vulns:list-create'),
            data=json.dumps({
                'audit_id': str(self.audit.id),
                'titre': 'CSRF Missing Token',
                'description': 'No CSRF check',
                'gravite': Gravite.MOYENNE,
                'scoreCVSS': 5.5,
                'codeCWE': 'CWE-352'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_create.status_code, 403)

    def test_vulns_synchroniser_api(self):
        res_sync = self.client.post(reverse('vulns:synchroniser'))
        self.assertEqual(res_sync.status_code, 200)
        data = res_sync.json()
        self.assertIn('message', data)

    def test_vuln_lifecycle_api(self):
        # Confirmer
        self.client.post(reverse('vulns:confirmer', kwargs={'vuln_id': self.vuln.id}))
        self.vuln.refresh_from_db()
        self.assertEqual(self.vuln.statut, StatutVulnerabilite.CONFIRMEE)

        # Faux positif
        self.client.post(reverse('vulns:faux-positif', kwargs={'vuln_id': self.vuln.id}))
        self.vuln.refresh_from_db()
        self.assertEqual(self.vuln.statut, StatutVulnerabilite.FAUX_POSITIF)

        # Corrigee
        self.client.post(reverse('vulns:corrigee', kwargs={'vuln_id': self.vuln.id}))
        self.vuln.refresh_from_db()
        self.assertEqual(self.vuln.statut, StatutVulnerabilite.CORRIGEE)

    def test_preuve_and_recommandation_api(self):
        # Preuve API
        res_p = self.client.post(
            reverse('vulns:preuves', kwargs={'vuln_id': self.vuln.id}),
            data=json.dumps({'type': 'HTTP_REQUEST', 'contenu': 'GET /test HTTP/1.1'}),
            content_type='application/json'
        )
        self.assertEqual(res_p.status_code, 201)

        # Recommandation API
        res_r = self.client.post(
            reverse('vulns:recommandations', kwargs={'vuln_id': self.vuln.id}),
            data=json.dumps({'description': 'Fix input sanitizer', 'priorite': Gravite.MOYENNE}),
            content_type='application/json'
        )
        self.assertEqual(res_r.status_code, 201)

    def test_seed_vulns_command(self):
        call_command('seed_vulns')
        self.assertTrue(Vulnerabilite.objects.filter(codeCWE='CWE-89').exists())
        self.assertTrue(Preuve.objects.exists())
        self.assertTrue(Recommandation.objects.exists())
