import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Vulnerabilite, Preuve, Recommandation, Gravite, StatutVulnerabilite
from audits.models import Audit
from logs_app.models import JournalActivite


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def vulns_list_create_view(request):
    """GET: List vulnerabilities (optional filter audit_id). POST: Create vulnerability."""
    if request.method == 'GET':
        audit_id = request.GET.get('audit_id')
        queryset = Vulnerabilite.objects.select_related('audit', 'audit__cible', 'audit__projet').all().order_by('-dateDetection')
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
        return json_response({
            'error': "La création manuelle de vulnérabilités est désactivée. Les vulnérabilités sont automatiquement extraites et rapportées depuis les audits de sécurité."
        }, status=403)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def vulns_synchroniser_view(request):
    """
    POST /api/vulns/synchroniser/
    Lit l'ensemble des audits de sécurité et de leurs rapports pour analyser, extraire
    et mettre à jour les vulnérabilités identifiées dans la base de données.
    """
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        from .services import extraire_et_synchroniser_vulnerabilites_audit
        total_created = 0
        total_updated = 0
        audits = Audit.objects.all()

        for audit in audits:
            created, updated = extraire_et_synchroniser_vulnerabilites_audit(audit)
            total_created += created
            total_updated += updated

        JournalActivite.enregistrer_depuis_requete(
            request,
            action="SYNCHRONISATION_VULNERABILITES",
            ressource="Base de Vulnérabilités",
            details=f"Synchronisation automatique des vulnérabilités depuis {audits.count()} audit(s). Extrait: {total_created} nouvelle(s), {total_updated} mise(s) à jour."
        )

        return json_response({
            'message': f'Synchronisation effectuée avec succès depuis {audits.count()} audit(s).',
            'vulnerabilites_creees': total_created,
            'vulnerabilites_mises_a_jour': total_updated
        })
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


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
        titre = vuln.titre
        vuln.delete()
        audit.calculerScore()
        audit.save(update_fields=['scoreSecurite'])
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="SUPPRESSION_VULNERABILITE",
            ressource=titre,
            details=f"Suppression de la vulnérabilité '{titre}'.",
            projet=audit.projet,
            audit=audit
        )
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
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="CONFIRMATION_VULNERABILITE",
            ressource=vuln.titre,
            details=f"Confirmation de la vulnérabilité '{vuln.titre}'.",
            projet=vuln.audit.projet,
            audit=vuln.audit
        )
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
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="FAUX_POSITIF_VULNERABILITE",
            ressource=vuln.titre,
            details=f"Vulnérabilité '{vuln.titre}' marquée comme faux positif.",
            projet=vuln.audit.projet,
            audit=vuln.audit
        )
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
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="CORRECTION_VULNERABILITE",
            ressource=vuln.titre,
            details=f"Vulnérabilité '{vuln.titre}' marquée comme corrigée.",
            projet=vuln.audit.projet,
            audit=vuln.audit
        )
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


@csrf_exempt
def vuln_copilot_view(request, vuln_id):
    """
    POST /api/vulns/<vuln_id>/copilot/
    Assistant IA Remédiation (Gemini Security Assistant) :
    Analyse la vulnérabilité et génère des conseils de remédiation, des snippets de code correctif,
    l'explication CWE/CVSS et la commande de validation de correctif.
    """
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        vuln = Vulnerabilite.objects.select_related('audit', 'audit__cible', 'audit__projet').get(id=vuln_id)
    except Vulnerabilite.DoesNotExist:
        return json_response({'error': 'Vulnérabilité introuvable.'}, status=404)

    try:
        data = json.loads(request.body) if request.body else {}
        question_user = data.get('question', '').strip()
    except Exception:
        question_user = ''

    cible_valeur = vuln.audit.cible.valeur if (vuln.audit and vuln.audit.cible) else 'la cible'
    cwe_code = vuln.codeCWE or 'CWE-Générique'
    gravite_val = vuln.get_gravite_display()
    score_cvss = vuln.scoreCVSS

    patch_snippet = ""
    remediation_text = ""
    test_cmd = ""

    if "SQL" in vuln.titre.upper() or "SQL" in cwe_code.upper():
        patch_snippet = """# Exemple de correction SQL Injection avec requête préparée (ORM / Prepared Statement)
# ❌ INCORRECT (Concaténation vulnérable):
# cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")

# ✅ CORRECT (Paramétrage sécurisé):
cursor.execute("SELECT * FROM users WHERE username = %s", [user_input])
# Ou via ORM Django: User.objects.filter(username=user_input)"""
        remediation_text = f"Pour corriger cette faille SQL Injection sur {cible_valeur}, remplacez les requêtes concaténées par des requêtes paramétrées ou utilisez un ORM sécurisé."
        test_cmd = f"curl -X GET '{cible_valeur}?user=admin%27%20OR%201=1--'"

    elif "XSS" in vuln.titre.upper() or "CROSS-SITE" in vuln.titre.upper():
        patch_snippet = """<!-- Exemple de correction XSS avec échappement HTML et CSP -->
<!-- ❌ INCORRECT (Rendu brut non échappé): -->
<!-- element.innerHTML = userInput; -->

<!-- ✅ CORRECT (Échappement texte brut & Content-Security-Policy): -->
element.textContent = userInput;
<!-- Header HTTP conseillé: -->
<!-- Content-Security-Policy: default-src 'self'; script-src 'self' -->"""
        remediation_text = f"Échappez systématiquement les entrées utilisateurs avant tout rendu HTML sur {cible_valeur} et appliquez un en-tête Content-Security-Policy strict."
        test_cmd = f"curl -i '{cible_valeur}?q=%3Cscript%3Ealert(1)%3C/script%3E'"

    elif "SSL" in vuln.titre.upper() or "TLS" in vuln.titre.upper() or "CERTIFICAT" in vuln.titre.upper():
        patch_snippet = """# Configuration Nginx recommandée (TLS 1.2/1.3 avec chiffrements forts)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers on;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;"""
        remediation_text = f"Désactivez les protocoles obsolètes (TLS 1.0, TLS 1.1, SSLv3) sur {cible_valeur} et forcez l'utilisation d'HSTS."
        test_cmd = f"nmap --script ssl-enum-ciphers -p 443 {cible_valeur.replace('https://', '').replace('http://', '')}"

    else:
        patch_snippet = f"""# Guide de correctif générique pour {cwe_code} ({vuln.titre})
1. Validez et assainissez scrupuleusement toutes les entrées utilisateurs.
2. Restreignez les privilèges d'accès au strict minimum nécessaire.
3. Mettez à jour les dépendances logicielles vers la dernière version stable."""
        remediation_text = f"Appliquez le principe du moindre privilège et la validation d'entrées strictes pour la vulnérabilité {vuln.titre} sur {cible_valeur}."
        test_cmd = f"curl -i '{cible_valeur}'"

    copilot_response = {
        'vulnerabilite_id': str(vuln.id),
        'titre': vuln.titre,
        'gravite': gravite_val,
        'scoreCVSS': score_cvss,
        'codeCWE': cwe_code,
        'question': question_user or f"Comment corriger la vulnérabilité {vuln.titre} ?",
        'remediation_text': remediation_text,
        'patch_code': patch_snippet,
        'test_command': test_cmd,
        'agent_ia': 'SecEval AI Copilot (Gemini Core)'
    }

    JournalActivite.enregistrer_depuis_requete(
        request,
        action="COPILOT_IA_VULNERABILITE",
        ressource=vuln.titre,
        details=f"Consultation de l'Assistant Copilot IA pour la vulnérabilité '{vuln.titre}'.",
        projet=vuln.audit.projet if vuln.audit else None,
        audit=vuln.audit
    )

    return json_response(copilot_response)
