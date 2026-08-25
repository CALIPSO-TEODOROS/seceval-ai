from django.core.management.base import BaseCommand
from reports.models import Rapport, FormatRapport, StatutRapport
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible


class Command(BaseCommand):
    help = "Peuple la base de données avec des rapports d'évaluation de sécurité."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Rapports ==="))

        audit = Audit.objects.first()
        if not audit:
            projet = Projet.creer(nom="Projet Report Demo", organisation="ReportCorp")
            cible = Cible.objects.create(projet=projet, valeur="https://app.reportcorp.io", type="URL")
            audit = Audit.objects.create(projet=projet, cible=cible, type=TypeAudit.STANDARD, statut=StatutAudit.TERMINE)
            audit.demarrer()
            audit.terminer()

        reports_data = [
            {'titre': "Rapport Synthétique d'Évaluation Web (HTML)", 'format': FormatRapport.HTML, 'statut': StatutRapport.PUBLIE},
            {'titre': "Export d'Audit Structuré (JSON)", 'format': FormatRapport.JSON, 'statut': StatutRapport.VALIDE},
            {'titre': "Document Officiel d'Audit Pentest (PDF)", 'format': FormatRapport.PDF, 'statut': StatutRapport.EN_REVISION},
            {'titre': "Matrice des Failles et Risques (CSV)", 'format': FormatRapport.CSV, 'statut': StatutRapport.BROUILLON}
        ]

        for r_item in reports_data:
            r, created = Rapport.objects.get_or_create(
                audit=audit,
                titre=r_item['titre'],
                defaults={'format': r_item['format'], 'statut': r_item['statut']}
            )
            r.generer()
            if r_item['statut'] == StatutRapport.VALIDE:
                r.valider()
            elif r_item['statut'] == StatutRapport.PUBLIE:
                r.publier()

            self.stdout.write(f"  [Rapport {r.format}] {r.titre} (Statut: {r.get_statut_display()}, Score: {r.scoreFinal}/100)")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Rapports terminé avec succès !"))
