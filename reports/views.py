import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Rapport, FormatRapport, StatutRapport
from audits.models import Audit
from logs_app.models import JournalActivite


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def reports_list_create_view(request):
    """GET: List reports. POST: Create a new report draft."""
    if request.method == 'GET':
        audit_id = request.GET.get('audit_id')
        queryset = Rapport.objects.select_related('audit', 'audit__cible').all()
        if audit_id:
            queryset = queryset.filter(audit_id=audit_id)

        reports_data = []
        for r in queryset:
            reports_data.append({
                'id': str(r.id),
                'audit': {
                    'id': str(r.audit.id),
                    'type': r.audit.get_type_display(),
                    'cible': r.audit.cible.valeur
                },
                'titre': r.titre,
                'format': r.format,
                'format_display': r.get_format_display(),
                'statut': r.statut,
                'statut_display': r.get_statut_display(),
                'scoreFinal': r.scoreFinal,
                'cheminFichier': r.cheminFichier,
                'dateGeneration': r.dateGeneration.isoformat(),
                'total_vulnerabilites': r.vulnerabilites.count()
            })
        return json_response({'rapports': reports_data, 'total': len(reports_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            audit_id = data.get('audit_id')
            titre = data.get('titre')
            report_format = data.get('format', FormatRapport.HTML)

            if not audit_id or not titre:
                return json_response({'error': 'Les champs audit_id et titre sont obligatoires.'}, status=400)

            audit = Audit.objects.get(id=audit_id)

            rapport = Rapport.objects.create(
                audit=audit,
                titre=titre,
                format=report_format,
                statut=StatutRapport.BROUILLON
            )

            # Auto-génération du fichier
            rapport.generer()

            JournalActivite.enregistrer_depuis_requete(
                request,
                action="CREATION_RAPPORT",
                ressource=rapport.titre,
                details=f"Création et génération du rapport [{rapport.format}] '{rapport.titre}'.",
                projet=audit.projet,
                audit=audit
            )

            return json_response({
                'message': 'Rapport d\'évaluation créé et généré avec succès.',
                'rapport': {
                    'id': str(rapport.id),
                    'titre': rapport.titre,
                    'format': rapport.format,
                    'statut': rapport.statut,
                    'scoreFinal': rapport.scoreFinal
                }
            }, status=201)
        except Audit.DoesNotExist:
            return json_response({'error': 'Audit introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def report_detail_view(request, report_id):
    """GET: Detail report with included vulnerabilities. DELETE: Delete report."""
    try:
        r = Rapport.objects.select_related('audit', 'audit__cible').get(id=report_id)
    except Rapport.DoesNotExist:
        return json_response({'error': 'Rapport introuvable.'}, status=404)

    if request.method == 'GET':
        vulns = [
            {
                'id': str(v.id),
                'titre': v.titre,
                'gravite': v.gravite,
                'scoreCVSS': v.scoreCVSS,
                'codeCWE': v.codeCWE,
                'statut': v.statut
            }
            for v in r.vulnerabilites.all()
        ]

        return json_response({
            'id': str(r.id),
            'audit': {'id': str(r.audit.id), 'cible': r.audit.cible.valeur},
            'titre': r.titre,
            'format': r.format,
            'format_display': r.get_format_display(),
            'statut': r.statut,
            'statut_display': r.get_statut_display(),
            'scoreFinal': r.scoreFinal,
            'cheminFichier': r.cheminFichier,
            'dateGeneration': r.dateGeneration.isoformat(),
            'vulnerabilites': vulns
        })

    elif request.method == 'DELETE':
        titre = r.titre
        audit = r.audit
        r.delete()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="SUPPRESSION_RAPPORT",
            ressource=titre,
            details=f"Suppression du rapport '{titre}'.",
            projet=audit.projet,
            audit=audit
        )
        return json_response({'message': 'Rapport supprimé avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def report_generer_view(request, report_id):
    """POST: Action generer()."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        r = Rapport.objects.get(id=report_id)
        r.generer()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="REGENERATION_RAPPORT",
            ressource=r.titre,
            details=f"Régénération du rapport '{r.titre}'.",
            projet=r.audit.projet,
            audit=r.audit
        )
        return json_response({
            'message': 'Fichier de rapport régénéré avec succès.',
            'statut': r.statut,
            'scoreFinal': r.scoreFinal,
            'cheminFichier': r.cheminFichier
        })
    except Rapport.DoesNotExist:
        return json_response({'error': 'Rapport introuvable.'}, status=404)


@csrf_exempt
def report_valider_view(request, report_id):
    """POST: Action valider()."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        r = Rapport.objects.get(id=report_id)
        r.valider()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="VALIDATION_RAPPORT",
            ressource=r.titre,
            details=f"Validation officielle du rapport '{r.titre}'.",
            projet=r.audit.projet,
            audit=r.audit
        )
        return json_response({'message': 'Rapport validé.', 'statut': r.statut})
    except Rapport.DoesNotExist:
        return json_response({'error': 'Rapport introuvable.'}, status=404)


@csrf_exempt
def report_publier_view(request, report_id):
    """POST: Action publier()."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        r = Rapport.objects.get(id=report_id)
        r.publier()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="PUBLICATION_RAPPORT",
            ressource=r.titre,
            details=f"Publication du rapport '{r.titre}'.",
            projet=r.audit.projet,
            audit=r.audit
        )
        return json_response({'message': 'Rapport publié avec succès.', 'statut': r.statut})
    except Rapport.DoesNotExist:
        return json_response({'error': 'Rapport introuvable.'}, status=404)


@csrf_exempt
def report_telecharger_view(request, report_id):
    """GET: Action telecharger() - Permet de télécharger/afficher le rapport."""
    if request.method != 'GET':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        r = Rapport.objects.get(id=report_id)
        content = r.telecharger()

        JournalActivite.enregistrer_depuis_requete(
            request,
            action="TELECHARGEMENT_RAPPORT",
            ressource=r.titre,
            details=f"Téléchargement du rapport [{r.format}] '{r.titre}'.",
            projet=r.audit.projet,
            audit=r.audit
        )

        content_types = {
            FormatRapport.JSON: 'application/json',
            FormatRapport.CSV: 'text/csv',
            FormatRapport.HTML: 'text/html',
            FormatRapport.PDF: 'text/html'  # Simulé
        }

        response = HttpResponse(content, content_type=content_types.get(r.format, 'text/plain'))
        ext = r.format.lower()
        response['Content-Disposition'] = f'inline; filename="rapport_audit_{r.id}.{ext}"'
        return response
    except Rapport.DoesNotExist:
        return json_response({'error': 'Rapport introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)
