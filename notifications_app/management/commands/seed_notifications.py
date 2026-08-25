from django.core.management.base import BaseCommand
from notifications_app.models import Notification, CanalNotification
from audits.models import Audit, TypeAudit, StatutAudit
from users.models import Utilisateur
from projects.models import Projet, Cible


class Command(BaseCommand):
    help = "Peuple la base de données avec des notifications de sécurité."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Notifications ==="))

        user = Utilisateur.objects.first()
        if not user:
            user = Utilisateur.objects.create_user(email="admin@seceval.io", nom="Admin Sécurité", password="AdminPassword123!")


        audit = Audit.objects.first()
        if not audit:
            projet = Projet.creer(nom="Projet Notif Demo", organisation="NotifCorp")
            cible = Cible.objects.create(projet=projet, valeur="https://app.notifcorp.io", type="URL")
            audit = Audit.objects.create(projet=projet, cible=cible, type=TypeAudit.STANDARD, statut=StatutAudit.EN_COURS)
            audit.demarrer()

        notifs_data = [
            {
                'canal': CanalNotification.EMAIL,
                'sujet': "🚨 [CRITIQUE] Vulnérabilité SQL Injection détectée sur https://app.fintechcorp.io",
                'message': "Une vulnérabilité critique CWE-89 (CVSS 9.8) a été confirmée lors de l'audit de sécurité."
            },
            {
                'canal': CanalNotification.SLACK,
                'sujet': "📢 Démarrage d'un audit de sécurité approfondi (Pentest)",
                'message': "L'audit de type APPROFONDI a été démarré avec succès par l'auditeur principal."
            },
            {
                'canal': CanalNotification.TELEGRAM,
                'sujet': "⚠️ Certificat SSL désuet ou expiré",
                'message': "Attention: Le serveur HTTPS utilise une suite TLS 1.0 dépréciée."
            },
            {
                'canal': CanalNotification.DISCORD,
                'sujet': "📄 Nouveau rapport d'évaluation publié",
                'message': "Le rapport d'audit au format HTML/PDF est désormais accessible et validé."
            }
        ]

        for item in notifs_data:
            n, created = Notification.objects.get_or_create(
                destinataire=user,
                audit=audit,
                sujet=item['sujet'],
                defaults={'canal': item['canal'], 'message': item['message'], 'statut': "EN_ATTENTE"}
            )
            sujet_clean = n.sujet.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(f"  [Notification {n.canal}] Envoyee a {n.destinataire.email} : {sujet_clean[:45]}...")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Notifications termine avec succes !"))

