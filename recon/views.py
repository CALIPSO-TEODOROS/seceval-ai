import json
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import TechnologieDetectee, ServiceDetecte, CertificatSSL
from audits.models import Audit


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def audit_recon_results_view(request, audit_id):
    """GET: Get all technical reconnaissance data for an audit."""
    try:
        audit = Audit.objects.select_related('cible', 'projet').get(id=audit_id)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)

    if request.method == 'GET':
        technologies = [
            {
                'id': str(t.id),
                'nom': t.nom,
                'version': t.version,
                'categorie': t.categorie,
                'niveauConfiance': t.niveauConfiance
            }
            for t in audit.technologies.all()
        ]

        services = [
            {
                'id': str(s.id),
                'port': s.port,
                'protocole': s.protocole,
                'service': s.service,
                'version': s.version,
                'etat': s.etat
            }
            for s in audit.services.all()
        ]

        certificats = [
            {
                'id': str(c.id),
                'sujet': c.sujet,
                'emetteur': c.emetteur,
                'dateDebut': c.dateDebut.isoformat(),
                'dateExpiration': c.dateExpiration.isoformat(),
                'valide': c.valide,
                'protocole': c.protocole
            }
            for c in audit.certificats_ssl.all()
        ]

        return json_response({
            'audit_id': str(audit.id),
            'cible': audit.cible.valeur,
            'technologies': technologies,
            'services': services,
            'certificats_ssl': certificats,
            'summary': {
                'total_technologies': len(technologies),
                'total_services': len(services),
                'total_certificats': len(certificats)
            }
        })

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def audit_recon_scan_simulation_view(request, audit_id):
    """POST: Simuler l'empreinte automatique par l'agent IA."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.select_related('cible').get(id=audit_id)

        # Nettoyage des anciennes ré-exécutions si souhaité ou ajout
        # Simulation d'empreinte stack selon le type de cible
        target_val = audit.cible.valeur.lower()

        # 1. Tech Stack
        techs_def = [
            {'nom': 'Django Framework', 'version': '5.0.2', 'categorie': 'Web Framework', 'niveauConfiance': 98.0},
            {'nom': 'Nginx HTTP Server', 'version': '1.24.0', 'categorie': 'Reverse Proxy / Web Server', 'niveauConfiance': 95.0},
            {'nom': 'PostgreSQL Database', 'version': '16.1', 'categorie': 'Relational DB', 'niveauConfiance': 90.0},
            {'nom': 'Bootstrap UI', 'version': '5.3.0', 'categorie': 'CSS Framework', 'niveauConfiance': 100.0}
        ]

        added_techs = []
        for t in techs_def:
            obj, _ = TechnologieDetectee.objects.get_or_create(
                audit=audit,
                nom=t['nom'],
                defaults={'version': t['version'], 'categorie': t['categorie'], 'niveauConfiance': t['niveauConfiance']}
            )
            added_techs.append(obj.nom)

        # 2. Services / Ports
        services_def = [
            {'port': 80, 'protocole': 'tcp', 'service': 'http', 'version': 'Nginx 1.24.0', 'etat': 'open'},
            {'port': 443, 'protocole': 'tcp', 'service': 'https', 'version': 'Nginx 1.24.0 (OpenSSL 3.0.2)', 'etat': 'open'},
            {'port': 22, 'protocole': 'tcp', 'service': 'ssh', 'version': 'OpenSSH 8.9p1', 'etat': 'open'},
            {'port': 5432, 'protocole': 'tcp', 'service': 'postgresql', 'version': 'PostgreSQL 16.1', 'etat': 'filtered'}
        ]

        added_services = []
        for s in services_def:
            obj, _ = ServiceDetecte.objects.get_or_create(
                audit=audit,
                port=s['port'],
                protocole=s['protocole'],
                defaults={'service': s['service'], 'version': s['version'], 'etat': s['etat']}
            )
            added_services.append(f"{s['port']}/{s['protocole']}")

        # 3. SSL Cert
        today = datetime.date.today()
        cert, _ = CertificatSSL.objects.get_or_create(
            audit=audit,
            sujet=f"CN={audit.cible.valeur}",
            defaults={
                'emetteur': "Let's Encrypt Authority X3",
                'dateDebut': today - datetime.timedelta(days=30),
                'dateExpiration': today + datetime.timedelta(days=60),
                'valide': True,
                'protocole': 'TLSv1.3'
            }
        )

        return json_response({
            'message': 'Scan de reconnaissance technique accompli avec succès par l\'agent IA.',
            'scan_summary': {
                'technologies_detectees': added_techs,
                'ports_ouverts': added_services,
                'certificat_ssl': cert.sujet
            }
        })

    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def create_technologie_view(request):
    """POST: Ajouter manuellement une technologie."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')
        nom = data.get('nom')
        version = data.get('version', '')
        categorie = data.get('categorie', '')
        niveauConfiance = data.get('niveauConfiance', 100.0)

        if not audit_id or not nom:
            return json_response({'error': 'Le champ audit_id et nom sont obligatoires.'}, status=400)

        audit = Audit.objects.get(id=audit_id)
        tech = TechnologieDetectee.objects.create(
            audit=audit,
            nom=nom,
            version=version,
            categorie=categorie,
            niveauConfiance=niveauConfiance
        )

        return json_response({
            'message': 'Technologie enregistrée avec succès.',
            'technologie': {
                'id': str(tech.id),
                'nom': tech.nom,
                'version': tech.version,
                'categorie': tech.categorie
            }
        }, status=201)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)


@csrf_exempt
def create_service_view(request):
    """POST: Ajouter manuellement un service détecté."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')
        port = data.get('port')
        service_name = data.get('service')
        protocole = data.get('protocole', 'tcp')
        version = data.get('version', '')
        etat = data.get('etat', 'open')

        if not audit_id or not port or not service_name:
            return json_response({'error': 'Les champs audit_id, port et service sont obligatoires.'}, status=400)

        audit = Audit.objects.get(id=audit_id)
        srv = ServiceDetecte.objects.create(
            audit=audit,
            port=port,
            protocole=protocole,
            service=service_name,
            version=version,
            etat=etat
        )

        return json_response({
            'message': 'Service réseau enregistré avec succès.',
            'service': {
                'id': str(srv.id),
                'port': srv.port,
                'protocole': srv.protocole,
                'service': srv.service,
                'etat': srv.etat
            }
        }, status=201)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)


@csrf_exempt
def create_ssl_view(request):
    """POST: Ajouter manuellement un certificat SSL/TLS."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')
        sujet = data.get('sujet')
        emetteur = data.get('emetteur')
        dateDebut = data.get('dateDebut')
        dateExpiration = data.get('dateExpiration')
        valide = data.get('valide', True)
        protocole = data.get('protocole', 'TLSv1.3')

        if not audit_id or not sujet or not emetteur or not dateDebut or not dateExpiration:
            return json_response({'error': 'Champs audit_id, sujet, emetteur, dateDebut et dateExpiration obligatoires.'}, status=400)

        if isinstance(dateDebut, str):
            dateDebut = datetime.date.fromisoformat(dateDebut)
        if isinstance(dateExpiration, str):
            dateExpiration = datetime.date.fromisoformat(dateExpiration)

        audit = Audit.objects.get(id=audit_id)
        cert = CertificatSSL.objects.create(
            audit=audit,
            sujet=sujet,
            emetteur=emetteur,
            dateDebut=dateDebut,
            dateExpiration=dateExpiration,
            valide=valide,
            protocole=protocole
        )

        return json_response({
            'message': 'Certificat SSL/TLS enregistré avec succès.',
            'certificat': {
                'id': str(cert.id),
                'sujet': cert.sujet,
                'emetteur': cert.emetteur,
                'valide': cert.valide
            }
        }, status=201)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
