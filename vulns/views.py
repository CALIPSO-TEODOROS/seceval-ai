import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Vulnerabilite, Preuve, Recommandation, Gravite, StatutVulnerabilite
from audits.models import Audit


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def vulns_list_create_view(request):
    """GET: List vulnerabilities (optional filter audit_id). POST: Create vulnerability."""
    if request.method == 'GET':
        audit_id = request.GET.get('audit_id')
        queryset = Vulnerabilite.objects.select_related('audit', 'audit__cible', 'audit__projet').all()
        if audit_id:
            queryset = queryset.filter(audit_id=audit_id)

        vulns_data = []
        for v in queryset:
            vulns_data.append({
                'id': str(v.id),
                'audit': {
                    'id': str(v.audit.id),
                    'type': v.audit.get_type_display(),
                    'cible': v.audit.cible.valeur
                },
                'titre': v.titre,
                'description': v.description,
                'gravite': v.gravite,
                'gravite_display': v.get_gravite_display(),
                'confiance': v.confiance,
                'scoreCVSS': v.scoreCVSS,
                'codeCWE': v.codeCWE,
                'statut': v.statut,
                'statut_display': v.get_statut_display(),
                'dateDetection': v.dateDetection.isoformat(),
                'total_preuves': v.preuves.count(),
                'total_recommandations': v.recommandations.count()
            })
        return json_response({'vulnerabilites': vulns_data, 'total': len(vulns_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            audit_id = data.get('audit_id')
            titre = data.get('titre')
            description = data.get('description', '')
            gravite = data.get('gravite', Gravite.MOYENNE)
            scoreCVSS = data.get('scoreCVSS', 5.0)
            codeCWE = data.get('codeCWE', '')
            confiance = data.get('confiance', 100.0)

            if not audit_id or not titre:
                return json_response({'error': 'Les champs audit_id et titre sont obligatoires.'}, status=400)

            audit = Audit.objects.get(id=audit_id)

            vuln = Vulnerabilite.objects.create(
                audit=audit,
                titre=titre,
                description=description,
                gravite=gravite,
                scoreCVSS=scoreCVSS,
                codeCWE=codeCWE,
                confiance=confiance,
                statut=StatutVulnerabilite.NOUVELLE
            )

            return json_response({
                'message': 'Vulnérabilité enregistrée avec succès.',
                'vulnerabilite': {
                    'id': str(vuln.id),
                    'titre': vuln.titre,
                    'gravite': vuln.gravite,
                    'scoreCVSS': vuln.scoreCVSS
                }
            }, status=201)
        except Audit.DoesNotExist:
            return json_response({'error': 'Audit introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def vuln_detail_view(request, vuln_id):
    """GET: Details with PoC proofs and recommendations. DELETE: Remove vulnerability."""
    try:
        vuln = Vulnerabilite.objects.select_related('audit', 'audit__cible').get(id=vuln_id)
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)

    if request.method == 'GET':
        preuves = [
            {
                'id': str(p.id),
                'type': p.type,
                'contenu': p.contenu,
                'fichier': p.fichier,
                'dateCreation': p.dateCreation.isoformat()
            }
            for p in vuln.preuves.all()
        ]

        recommandations = [
            {
                'id': str(r.id),
                'description': r.description,
                'priorite': r.priorite,
                'composantConcerne': r.composantConcerne,
                'methodeValidation': r.methodeValidation
            }
            for r in vuln.recommandations.all()
        ]

        return json_response({
            'id': str(vuln.id),
            'audit': {'id': str(vuln.audit.id), 'cible': vuln.audit.cible.valeur},
            'titre': vuln.titre,
            'description': vuln.description,
            'gravite': vuln.gravite,
            'gravite_display': vuln.get_gravite_display(),
            'confiance': vuln.confiance,
            'scoreCVSS': vuln.scoreCVSS,
            'codeCWE': vuln.codeCWE,
            'statut': vuln.statut,
            'statut_display': vuln.get_statut_display(),
            'dateDetection': vuln.dateDetection.isoformat(),
            'preuves': preuves,
            'recommandations': recommandations
        })

    elif request.method == 'DELETE':
        audit = vuln.audit
        vuln.delete()
        audit.calculerScore()
        audit.save(update_fields=['scoreSecurite'])
        return json_response({'message': 'Vulnérabilité supprimée avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def vuln_confirmer_view(request, vuln_id):
    """POST: Confirmer une vulnérabilité (confirmer())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        vuln = Vulnerabilite.objects.get(id=vuln_id)
        vuln.confirmer()
        return json_response({'message': 'Vulnérabilité confirmée.', 'statut': vuln.statut})
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)


@csrf_exempt
def vuln_faux_positif_view(request, vuln_id):
    """POST: Marquer comme faux positif (marquerFauxPositif())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        vuln = Vulnerabilite.objects.get(id=vuln_id)
        vuln.marquerFauxPositif()
        return json_response({'message': 'Vulnérabilité marquée comme faux positif.', 'statut': vuln.statut})
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)


@csrf_exempt
def vuln_corrigee_view(request, vuln_id):
    """POST: Marquer comme corrigée (marquerCorrigee())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        vuln = Vulnerabilite.objects.get(id=vuln_id)
        vuln.marquerCorrigee()
        return json_response({'message': 'Vulnérabilité marquée comme corrigée.', 'statut': vuln.statut})
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)


@csrf_exempt
def vuln_classifier_view(request, vuln_id):
    """POST: Reclassifier la sévérité/CVSS/CWE (classifier())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        data = json.loads(request.body)
        gravite = data.get('gravite')
        scoreCVSS = data.get('scoreCVSS')
        codeCWE = data.get('codeCWE')

        vuln = Vulnerabilite.objects.get(id=vuln_id)
        vuln.classifier(gravite=gravite, scoreCVSS=scoreCVSS, codeCWE=codeCWE)

        return json_response({
            'message': 'Vulnérabilité reclassifiée avec succès.',
            'vulnerabilite': {
                'id': str(vuln.id),
                'gravite': vuln.gravite,
                'scoreCVSS': vuln.scoreCVSS,
                'codeCWE': vuln.codeCWE
            }
        })
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)


@csrf_exempt
def vuln_preuves_view(request, vuln_id):
    """GET: Lister les preuves PoC. POST: Ajouter une preuve PoC."""
    try:
        vuln = Vulnerabilite.objects.get(id=vuln_id)
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)

    if request.method == 'GET':
        preuves = [
            {'id': str(p.id), 'type': p.type, 'contenu': p.contenu, 'fichier': p.fichier, 'dateCreation': p.dateCreation.isoformat()}
            for p in vuln.preuves.all()
        ]
        return json_response({'preuves': preuves})

    elif request.method == 'POST':
        data = json.loads(request.body)
        type_preuve = data.get('type', 'HTTP_REQUEST')
        contenu = data.get('contenu')
        fichier = data.get('fichier', '')

        if not contenu:
            return json_response({'error': 'Le contenu de la preuve est obligatoire.'}, status=400)

        preuve = Preuve.objects.create(vulnerabilite=vuln, type=type_preuve, contenu=contenu, fichier=fichier)
        return json_response({'message': 'Preuve PoC ajoutée avec succès.', 'preuve': {'id': str(preuve.id), 'type': preuve.type}}, status=201)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def vuln_recommandations_view(request, vuln_id):
    """GET: Lister les recommandations. POST: Ajouter une recommandation."""
    try:
        vuln = Vulnerabilite.objects.get(id=vuln_id)
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)

    if request.method == 'GET':
        recs = [
            {'id': str(r.id), 'description': r.description, 'priorite': r.priorite, 'composantConcerne': r.composantConcerne, 'methodeValidation': r.methodeValidation}
            for r in vuln.recommandations.all()
        ]
        return json_response({'recommandations': recs})

    elif request.method == 'POST':
        data = json.loads(request.body)
        description = data.get('description')
        priorite = data.get('priorite', Gravite.MOYENNE)
        composantConcerne = data.get('composantConcerne', '')
        methodeValidation = data.get('methodeValidation', '')

        if not description:
            return json_response({'error': 'La description de la recommandation est obligatoire.'}, status=400)

        rec = Recommandation.objects.create(
            vulnerabilite=vuln,
            description=description,
            priorite=priorite,
            composantConcerne=composantConcerne,
            methodeValidation=methodeValidation
        )
        return json_response({'message': 'Recommandation de patch ajoutée.', 'recommandation': {'id': str(rec.id), 'priorite': rec.priorite}}, status=201)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)
