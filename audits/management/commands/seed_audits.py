from django.core.management.base import BaseCommand
from django.utils import timezone
from audits.models import (
    Audit,
    PlanAudit,
    EtapeAudit,
    TypeAudit,
    StatutAudit,
    StatutExecution
)
from projects.models import Projet, Cible
from users.models import Utilisateur


class Command(BaseCommand):
    help = "Peuple la base de données avec des audits de sécurité, plans et étapes initiaux."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder d'Audits ==="))

        projet = Projet.objects.first()
        if not projet:
            projet = Projet.creer(nom="Projet Demo Audits", organisation="DemoCorp")

        cible1 = Cible.objects.filter(projet=projet).first()
        if not cible1:
            cible1 = Cible.objects.create(
                projet=projet,
                valeur="https://app.democorp.io",
                type="URL"
            )

        user = Utilisateur.objects.filter(email="auditeur@seceval.io").first()

        # Audit 1: Terminé avec score (Planification Unique)
        audit1 = Audit.objects.create(
            titre="Evaluation Annuelle OWASP Top 10",
            contexte="Audit complet de sécurité pré-certification ISO 27001 sur le portail applicatif web.",
            projet=projet,
            cible=cible1,
            lancePar=user,
            type=TypeAudit.STANDARD,
            statut=StatutAudit.TERMINE,
            typePlanification="UNIQUE",
            frequence="AUCUNE",
            scoreSecurite=90.0,
            progression=100
        )
        audit1.demarrer()
        # Mark all steps completed
        for etape in audit1.plan.etapes.all():
            etape.statut = StatutExecution.COMPLETED
            etape.save()
        audit1.terminer()
        self.stdout.write(f"  [Audit Terminé] {audit1.titre} ({audit1.type}) sur {audit1.cible.valeur} (Score: {audit1.scoreSecurite}/100)")

        # Audit 2: En Cours (Planification Répétitive Hebdomadaire)
        audit2 = Audit.objects.create(
            titre="Scan Récurrent des Endpoints API REST & BOLA",
            contexte="Audit de sécurité automatisé hebdomadaire ciblant les mécanismes de contrôle d'accès BOLA/IDOR et sérialisation JWT.",
            projet=projet,
            cible=cible1,
            lancePar=user,
            type=TypeAudit.API,
            statut=StatutAudit.EN_COURS,
            typePlanification="REPETITIVE",
            frequence="HEBDOMADAIRE",
            heureExecution=timezone.datetime.strptime("14:30", "%H:%M").time(),
            prochaineExecution=timezone.now() + timezone.timedelta(days=7),
            webhookN8nUrl="https://n8n.zendaya.tech/webhook-test/ad59815e-2809-4f25-a120-b24b5f02a831",
            progression=40
        )
        audit2.demarrer()
        etapes2 = list(audit2.plan.etapes.all())
        if len(etapes2) >= 2:
            etapes2[0].statut = StatutExecution.COMPLETED
            etapes2[0].save()
            etapes2[1].statut = StatutExecution.RUNNING
            etapes2[1].save()
        self.stdout.write(f"  [Audit En Cours] {audit2.titre} ({audit2.type}) sur {audit2.cible.valeur} [Répétitive: {audit2.frequence} @ {audit2.heureExecution}] (Progression: 40%)")

        # Audit 3: En Attente
        audit3 = Audit.objects.create(
            titre="Contrôle de Conformité SSL / TLS & Ciphers",
            contexte="Vérification régulière de la validité du certificat SSL, des suites de chiffrement et de la configuration HSTS.",
            projet=projet,
            cible=cible1,
            lancePar=user,
            type=TypeAudit.SSL_TLS,
            statut=StatutAudit.EN_ATTENTE,
            typePlanification="UNIQUE",
            frequence="AUCUNE",
            heureExecution=timezone.datetime.strptime("09:00", "%H:%M").time(),
            webhookN8nUrl="https://n8n.seceval.io/webhook/audit-trigger-ssl"
        )

        self.stdout.write(f"  [Audit En Attente] {audit3.titre} ({audit3.type}) sur {audit3.cible.valeur}")


        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Audits terminé avec succès !"))
