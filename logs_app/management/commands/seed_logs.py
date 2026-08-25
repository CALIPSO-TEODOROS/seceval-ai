from django.core.management.base import BaseCommand
from logs_app.models import JournalActivite
from audits.models import Audit, TypeAudit, StatutAudit
from users.models import Utilisateur
from projects.models import Projet, Cible


class Command(BaseCommand):
    help = "Peuple la base de données avec des journaux d'activité et d'audit."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Journalisation ==="))

        user = Utilisateur.objects.first()
        if not user:
            user = Utilisateur.objects.create_user(email="admin@seceval.io", nom="Admin Sécurité", password="AdminPassword123!")

        projet = Projet.objects.first()
        if not projet:
            projet = Projet.creer(nom="Projet Log Demo", organisation="LogCorp")

        audit = Audit.objects.first()
        if not audit:
            cible = Cible.objects.create(projet=projet, valeur="https://app.logcorp.io", type="URL")
            audit = Audit.objects.create(projet=projet, cible=cible, type=TypeAudit.STANDARD, statut=StatutAudit.EN_COURS)
            audit.demarrer()

        logs_data = [
            {
                'action': "CONNEXION_UTILISATEUR",
                'ressource': "Formulaire de Connexion",
                'details': "Connexion réussie depuis le portail Web SPA",
                'adresseIP': "192.168.1.100"
            },
            {
                'action': "CREATION_PROJET",
                'ressource': f"Projet: {projet.nom}",
                'details': f"Projet créé avec succès pour {projet.organisation}",
                'adresseIP': "192.168.1.100",
                'projet': projet
            },
            {
                'action': "DEMARRAGE_AUDIT",
                'ressource': f"Audit: {audit.cible.valeur}",
                'details': "Audit de sécurité initialisé et démarré automaiquement",
                'adresseIP': "10.0.0.45",
                'projet': projet,
                'audit': audit
            },
            {
                'action': "DETECTION_VULNERABILITE",
                'ressource': "SQL Injection CWE-89",
                'details': "Vulnérabilité critique confirmée par le scanner actif",
                'adresseIP': "10.0.0.45",
                'audit': audit
            },
            {
                'action': "PUBLICATION_RAPPORT",
                'ressource': "Rapport d'Audit Pentest (HTML)",
                'details': "Le rapport d'évaluation final a été validé et publié",
                'adresseIP': "192.168.1.100",
                'projet': projet,
                'audit': audit
            }
        ]

        for item in logs_data:
            j = JournalActivite.enregistrer(
                utilisateur=user,
                action=item['action'],
                ressource=item['ressource'],
                details=item['details'],
                adresseIP=item['adresseIP'],
                projet=item.get('projet'),
                audit=item.get('audit')
            )
            action_clean = j.action.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(f"  [Log] {j.utilisateur.email} -> {action_clean} ({j.ressource})")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Journalisation termine avec succes !"))
