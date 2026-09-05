import os
from django.utils import timezone
from vulns.models import Vulnerabilite, Preuve, Recommandation, Gravite, StatutVulnerabilite


def extraire_et_synchroniser_vulnerabilites_audit(audit):
    """
    Rapporte et met à jour automatiquement les vulnérabilités identifiées dans les audits de sécurité.
    Lit le résultat brut n8n, les exécutions et les rapports d'audit pour alimenter la table des vulnérabilités.
    """
    count_created = 0
    count_updated = 0

    raw_data = audit.resultatBrutN8n or {}
    items = []

    if isinstance(raw_data, dict):
        items = raw_data.get('vulnerabilites') or raw_data.get('vulnerabilities') or raw_data.get('findings') or []

    # 1. Extraction si des données structurées sont présentes
    if isinstance(items, list) and len(items) > 0:
        for item in items:
            titre = item.get('titre') or item.get('title') or 'Vulnérabilité Identifiée'
            codeCWE = item.get('codeCWE') or item.get('cwe') or ''
            gravite_str = str(item.get('gravite') or item.get('severity') or 'MOYENNE').upper()
            
            gravite = Gravite.MOYENNE
            if 'CRITIQUE' in gravite_str or 'CRITICAL' in gravite_str:
                gravite = Gravite.CRITIQUE
            elif 'ELEV' in gravite_str or 'HIGH' in gravite_str:
                gravite = Gravite.ELEVEE
            elif 'FAIBLE' in gravite_str or 'LOW' in gravite_str:
                gravite = Gravite.FAIBLE
            elif 'INFO' in gravite_str:
                gravite = Gravite.INFORMATION

            scoreCVSS = float(item.get('scoreCVSS') or item.get('cvss') or 5.0)
            desc = item.get('description') or f"Vulnérabilité détectée lors de l'audit '{audit.titre or audit.cible.valeur}'."

            vuln, created = Vulnerabilite.objects.get_or_create(
                audit=audit,
                titre=titre,
                defaults={
                    'description': desc,
                    'gravite': gravite,
                    'scoreCVSS': scoreCVSS,
                    'codeCWE': codeCWE,
                    'statut': StatutVulnerabilite.CONFIRMEE
                }
            )
            if created:
                count_created += 1
            else:
                vuln.description = desc
                vuln.gravite = gravite
                vuln.scoreCVSS = scoreCVSS
                vuln.codeCWE = codeCWE
                vuln.save()
                count_updated += 1

            poc = item.get('poc') or item.get('proof')
            if poc and not vuln.preuves.filter(contenu=poc).exists():
                Preuve.objects.create(vulnerabilite=vuln, type="POC_HTTP", contenu=poc)

            recom = item.get('recommandation') or item.get('fix')
            if recom and not vuln.recommandations.filter(description=recom).exists():
                Recommandation.objects.create(vulnerabilite=vuln, description=recom, priorite=gravite)

    # 2. Extraction textuelle depuis les rapports et exécutions si aucune donnée structurée n'a été extraite
    if count_created == 0 and count_updated == 0:
        report_texts = []
        for ex in audit.executions.all():
            if ex.rapportText:
                report_texts.append(ex.rapportText)
        for rap in audit.rapports.all():
            if rap.cheminFichier and os.path.exists(rap.cheminFichier):
                try:
                    with open(rap.cheminFichier, 'r', encoding='utf-8') as f:
                        report_texts.append(f.read())
                except Exception:
                    pass

        combined_text = (" ".join(report_texts) + " " + str(raw_data)).lower()

        catalog = [
            {
                'titre': "Injection SQL sur paramètre vulnérable",
                'codeCWE': "CWE-89",
                'gravite': Gravite.CRITIQUE,
                'scoreCVSS': 9.8,
                'desc': "Détection d'une vulnérabilité d'injection SQL (SQLi). Les requêtes de base de données doivent être paramétrées pour éviter l'exécution de commandes non autorisées.",
                'keywords': ['sql', 'cwe-89', 'sqli', 'injection']
            },
            {
                'titre': "Cross-Site Scripting (XSS) réfléchi / stocké",
                'codeCWE': "CWE-79",
                'gravite': Gravite.ELEVEE,
                'scoreCVSS': 7.5,
                'desc': "Vulnérabilité d'injection de script côté client. Permet d'exécuter du code JavaScript arbitraire dans la session de la victime.",
                'keywords': ['xss', 'cwe-79', 'cross-site', 'scripting']
            },
            {
                'titre': "Prise en charge de suites de chiffrement SSL/TLS obsolètes",
                'codeCWE': "CWE-326",
                'gravite': Gravite.MOYENNE,
                'scoreCVSS': 5.3,
                'desc': "Le serveur web accepte des protocoles dépréciés (TLS 1.0 / TLS 1.1) exposant le trafic aux attaques Man-in-the-Middle.",
                'keywords': ['tls', 'ssl', 'cwe-326', 'cipher', 'chiffrement']
            },
            {
                'titre': "Absence de contrôle d'accès au niveau objet (BOLA)",
                'codeCWE': "CWE-639",
                'gravite': Gravite.ELEVEE,
                'scoreCVSS': 8.1,
                'desc': "Les endpoints API REST ne vérifient pas les autorisations de l'utilisateur sur la ressource demandée.",
                'keywords': ['bola', 'cwe-639', 'authorization', 'api']
            }
        ]

        for entry in catalog:
            if any(kw in combined_text for kw in entry['keywords']):
                vuln, created = Vulnerabilite.objects.get_or_create(
                    audit=audit,
                    titre=entry['titre'],
                    defaults={
                        'description': entry['desc'],
                        'gravite': entry['gravite'],
                        'scoreCVSS': entry['scoreCVSS'],
                        'codeCWE': entry['codeCWE'],
                        'statut': StatutVulnerabilite.CONFIRMEE
                    }
                )
                if created:
                    count_created += 1
                    Preuve.objects.create(vulnerabilite=vuln, type="AUTOMATED_EXTRACTION", contenu=f"Rapporté automatiquement depuis l'audit '{audit.titre}' sur {audit.cible.valeur}.")
                    Recommandation.objects.create(vulnerabilite=vuln, description=f"Appliquer le correctif recommandé pour la vulnérabilité {entry['codeCWE']}.", priorite=entry['gravite'])
                else:
                    count_updated += 1

    # Recalculer le score de l'audit si des vulnérabilités ont été extraites ou mises à jour
    if count_created > 0 or count_updated > 0:
        audit.calculerScore()
        audit.save(update_fields=['scoreSecurite'])

    return count_created, count_updated
