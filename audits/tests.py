import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from audits.models import (
    Audit,
    PlanAudit,
    EtapeAudit,
    TypeAudit,
    StatutAudit,
    StatutExecution
)
from projects.models import Projet, Cible, TypeCible
from users.models import Utilisateur


class AuditManagementModelTests(TestCase):

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email="auditor_test@secframe.io",
            nom="Test Auditor",
            password="Password123!"
        )
        self.projet = Projet.creer(nom="Projet Test Audit", organisation="Org Audit")
        self.cible = Cible.objects.create(
            projet=self.projet,
            valeur="https://audit-target.io",
            type=TypeCible.URL
        )
        self.audit = Audit.objects.create(
            projet=self.projet,
            cible=self.cible,
            lancePar=self.user,
            type=TypeAudit.STANDARD
        )

    def test_audit_creation(self):
        self.assertIsInstance(self.audit.id, uuid.UUID)
        self.assertEqual(self.audit.statut, StatutAudit.EN_ATTENTE)
        self.assertEqual(self.audit.scoreSecurite, 0.0)
        self.assertEqual(self.audit.progression, 0)

    def test_audit_demarrer_and_plan_generation(self):
        self.audit.demarrer()
        self.audit.refresh_from_db()
        self.assertEqual(self.audit.statut, StatutAudit.EN_COURS)
        self.assertIsNotNone(self.audit.dateDebut)
        self.assertTrue(hasattr(self.audit, 'plan'))

        plan = self.audit.plan
        self.assertGreaterEqual(plan.etapes.count(), 3)

        # Check default steps
        first_step = plan.etapes.first()
        self.assertEqual(first_step.statut, StatutExecution.PENDING)

    def test_audit_lifecycle_methods(self):
        self.audit.demarrer()

        # Pause
        self.audit.mettreEnPause()
        self.assertEqual(self.audit.statut, StatutAudit.PLANIFICATION)

        # Terminer and Score Calculation
        # Complete all steps
        plan = self.audit.plan
        for step in plan.etapes.all():
            step.statut = StatutExecution.COMPLETED
            step.save()

        self.audit.terminer()
        self.audit.refresh_from_db()
        self.assertEqual(self.audit.statut, StatutAudit.TERMINE)
        self.assertEqual(self.audit.progression, 100)
        self.assertEqual(self.audit.scoreSecurite, 100.0)
        self.assertIsNotNone(self.audit.dateFin)

    def test_plan_audit_ajouter_and_reordonner(self):
        self.audit.demarrer()
        plan = self.audit.plan
        count_before = plan.etapes.count()

        etape_nouvelle = plan.ajouterEtape(nom="Étape Personnalisée IA")
        self.assertEqual(plan.etapes.count(), count_before + 1)
        self.assertEqual(etape_nouvelle.nom, "Étape Personnalisée IA")

        plan.reordonnerEtapes()
        self.assertEqual(plan.etapes.last().ordre, plan.etapes.count())


class AuditAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = Utilisateur.objects.create_user(
            email="api_auditor@secframe.io",
            nom="API Auditor",
            password="Password123!"
        )
        self.projet = Projet.creer(nom="Audit API Project", organisation="API Org")
        self.cible = Cible.objects.create(
            projet=self.projet,
            valeur="https://api-audit-target.io",
            type=TypeCible.API_REST
        )
        self.audit = Audit.objects.create(
            projet=self.projet,
            cible=self.cible,
            lancePar=self.user,
            type=TypeAudit.API
        )

    def test_audits_list_and_create_api(self):
        # GET List
        res = self.client.get(reverse('audits:list-create'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data['total'], 1)

        # POST Create Audit with Titre, Contexte, Heure Execution and Webhook n8n
        res_create = self.client.post(
            reverse('audits:list-create'),
            data=json.dumps({
                'projet_id': str(self.projet.id),
                'cible_id': str(self.cible.id),
                'type': TypeAudit.SSL_TLS,
                'titre': 'Audit SSL/TLS Hebdomadaire',
                'contexte': 'Vérification automatisée des certificats et protocoles de chiffrement.',
                'typePlanification': 'REPETITIVE',
                'frequence': 'HEBDOMADAIRE',
                'heureExecution': '14:30',
                'webhookN8nUrl': 'https://n8n.seceval.io/webhook/audit-trigger-test'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.json()['audit']
        self.assertEqual(created_data['titre'], 'Audit SSL/TLS Hebdomadaire')
        self.assertEqual(created_data['typePlanification'], 'REPETITIVE')
        self.assertEqual(created_data['frequence'], 'HEBDOMADAIRE')
        self.assertEqual(created_data['heureExecution'], '14:30')
        self.assertEqual(created_data['webhookN8nUrl'], 'https://n8n.seceval.io/webhook/audit-trigger-test')



    def test_audit_detail_demarrer_terminer_api(self):
        detail_url = reverse('audits:detail', kwargs={'audit_id': self.audit.id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, 200)

        # POST Demarrer
        demarrer_url = reverse('audits:demarrer', kwargs={'audit_id': self.audit.id})
        res_start = self.client.post(demarrer_url)
        self.assertEqual(res_start.status_code, 200)

        self.audit.refresh_from_db()
        self.assertEqual(self.audit.statut, StatutAudit.EN_COURS)

        # Update step
        first_step = self.audit.plan.etapes.first()
        etape_url = reverse('audits:update-etape', kwargs={'etape_id': first_step.id})
        res_etape = self.client.post(
            etape_url,
            data=json.dumps({'statut': StatutExecution.COMPLETED}),
            content_type='application/json'
        )
        self.assertEqual(res_etape.status_code, 200)

        # POST Terminer
        terminer_url = reverse('audits:terminer', kwargs={'audit_id': self.audit.id})
        res_finish = self.client.post(terminer_url)
        self.assertEqual(res_finish.status_code, 200)
        self.audit.refresh_from_db()
        self.assertEqual(self.audit.statut, StatutAudit.TERMINE)

    def test_seed_audits_command(self):
        call_command('seed_audits')
        self.assertTrue(Audit.objects.filter(type=TypeAudit.STANDARD).exists())
        self.assertTrue(Audit.objects.filter(type=TypeAudit.API).exists())
