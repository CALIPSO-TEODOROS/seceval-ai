import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import (
    Projet,
    Cible,
    AutorisationCible,
    StatutProjet,
    TypeCible,
    Environnement,
    StatutCible
)


class Command(BaseCommand):
    help = "Peuple la base de données avec des projets, cibles et autorisations de sécurité initiaux."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Projets ==="))

        # 1. Projets
        p1 = Projet.creer(
            nom="Evaluation Banque En Ligne",
            organisation="FintechCorp",
            description="Audit complet des services bancaires web et API mobile.",
            statut=StatutProjet.ACTIF
        )
        self.stdout.write(f"  [Projet] {p1.nom} ({p1.organisation})")

        p2 = Projet.creer(
            nom="Audit Portail E-Commerce",
            organisation="RetailGlobal",
            description="Recherche de vulnérabilités OWASP Top 10 sur la plateforme marchand.",
            statut=StatutProjet.ACTIF
        )
        self.stdout.write(f"  [Projet] {p2.nom} ({p2.organisation})")

        p3 = Projet.creer(
            nom="Scan Infrastructure Interne",
            organisation="CyberSecLab",
            description="Campagne de pentest sur les réseaux et API internes.",
            statut=StatutProjet.BROUILLON
        )
        self.stdout.write(f"  [Projet] {p3.nom} ({p3.organisation})")

        # 2. Cibles
        c1 = Cible.objects.create(
            projet=p1,
            valeur="https://app.fintechcorp.io",
            type=TypeCible.URL,
            environnement=Environnement.PREPRODUCTION,
            statut=StatutCible.AUTORISEE
        )
        self.stdout.write(f"  [Cible] {c1.valeur} [{c1.type}]")

        c2 = Cible.objects.create(
            projet=p2,
            valeur="https://api.retailglobal.com/v1",
            type=TypeCible.API_REST,
            environnement=Environnement.PRODUCTION,
            statut=StatutCible.EN_ATTENTE
        )
        self.stdout.write(f"  [Cible] {c2.valeur} [{c2.type}]")

        c3 = Cible.objects.create(
            projet=p3,
            valeur="192.168.10.50",
            type=TypeCible.ADRESSE_IP,
            environnement=Environnement.TEST,
            statut=StatutCible.AUTORISEE
        )
        self.stdout.write(f"  [Cible] {c3.valeur} [{c3.type}]")

        # 3. Autorisations de cibles
        today = timezone.now().date()
        date_debut = today - datetime.timedelta(days=30)
        date_fin = today + datetime.timedelta(days=335)

        a1 = AutorisationCible.objects.create(
            cible=c1,
            dateDebut=date_debut,
            dateFin=date_fin,
            preuve="CERT-AUTH-FINTECH-2026-001.pdf",
            testsActifsAutorises=True,
            commentaire="Autorisation écrite signée par le RSSI de FintechCorp."
        )
        c1.verifierAutorisation()
        self.stdout.write(f"  [Autorisation] {a1.preuve} (Valide: {a1.estValide()})")

        a2 = AutorisationCible.objects.create(
            cible=c3,
            dateDebut=date_debut,
            dateFin=date_fin,
            preuve="CERT-AUTH-CYBERSEC-2026-002.pdf",
            testsActifsAutorises=False,
            commentaire="Scan passif uniquement sur l'IP du laboratoire."
        )
        c3.verifierAutorisation()
        self.stdout.write(f"  [Autorisation] {a2.preuve} (Valide: {a2.estValide()})")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Projets termine avec succes !"))
