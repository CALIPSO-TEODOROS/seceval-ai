import datetime
from django.core.management.base import BaseCommand
from recon.models import TechnologieDetectee, ServiceDetecte, CertificatSSL
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible


class Command(BaseCommand):
    help = "Peuple la base de données avec des résultats de reconnaissance technique (Technologies, Services, SSL)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Reconnaissance Technique ==="))

        audit = Audit.objects.first()
        if not audit:
            projet = Projet.creer(nom="Projet Recon Demo", organisation="ReconCorp")
            cible = Cible.objects.create(projet=projet, valeur="https://app.reconcorp.io", type="URL")
            audit = Audit.objects.create(projet=projet, cible=cible, type=TypeAudit.STANDARD, statut=StatutAudit.EN_COURS)
            audit.demarrer()

        # 1. Technologies
        techs = [
            {'nom': 'Django Web Framework', 'version': '5.0.2', 'categorie': 'Backend Framework', 'niveauConfiance': 98.5},
            {'nom': 'React UI Library', 'version': '18.2.0', 'categorie': 'Frontend Framework', 'niveauConfiance': 95.0},
            {'nom': 'Nginx Reverse Proxy', 'version': '1.24.0', 'categorie': 'Web Server', 'niveauConfiance': 100.0},
            {'nom': 'PostgreSQL Database', 'version': '16.1', 'categorie': 'Database', 'niveauConfiance': 92.0},
            {'nom': 'OpenSSL Crypto', 'version': '3.0.2', 'categorie': 'Security Library', 'niveauConfiance': 99.0}
        ]

        for t in techs:
            obj, created = TechnologieDetectee.objects.get_or_create(
                audit=audit,
                nom=t['nom'],
                defaults={'version': t['version'], 'categorie': t['categorie'], 'niveauConfiance': t['niveauConfiance']}
            )
            self.stdout.write(f"  [Technologie] {obj.nom} {obj.version} ({obj.categorie})")

        # 2. Services / Ports
        services = [
            {'port': 80, 'protocole': 'tcp', 'service': 'http', 'version': 'Nginx 1.24.0', 'etat': 'open'},
            {'port': 443, 'protocole': 'tcp', 'service': 'https', 'version': 'Nginx (TLSv1.3)', 'etat': 'open'},
            {'port': 22, 'protocole': 'tcp', 'service': 'ssh', 'version': 'OpenSSH 8.9p1', 'etat': 'open'},
            {'port': 8080, 'protocole': 'tcp', 'service': 'http-proxy', 'version': 'Gunicorn 21.2.0', 'etat': 'open'},
            {'port': 5432, 'protocole': 'tcp', 'service': 'postgresql', 'version': 'PostgreSQL 16.1', 'etat': 'filtered'}
        ]

        for s in services:
            obj, created = ServiceDetecte.objects.get_or_create(
                audit=audit,
                port=s['port'],
                protocole=s['protocole'],
                defaults={'service': s['service'], 'version': s['version'], 'etat': s['etat']}
            )
            self.stdout.write(f"  [Service] Port {obj.port}/{obj.protocole} - {obj.service} [{obj.etat}]")

        # 3. Certificat SSL
        today = datetime.date.today()
        cert, created = CertificatSSL.objects.get_or_create(
            audit=audit,
            sujet=f"CN={audit.cible.valeur}",
            defaults={
                'emetteur': "Let's Encrypt Authority X3",
                'dateDebut': today - datetime.timedelta(days=45),
                'dateExpiration': today + datetime.timedelta(days=45),
                'valide': True,
                'protocole': 'TLSv1.3'
            }
        )
        self.stdout.write(f"  [Certificat SSL] {cert.sujet} (Émetteur: {cert.emetteur})")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Reconnaissance Technique terminé avec succès !"))
