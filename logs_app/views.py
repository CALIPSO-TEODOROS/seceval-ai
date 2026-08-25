import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import JournalActivite
from users.models import Utilisateur
from projects.models import Projet
from audits.models import Audit


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def logs_list_create_view(request):
    """GET: List activity logs. POST: Record an activity log."""
    if request.method == 'GET':
        user_id = request.GET.get('utilisateur_id')
        project_id = request.GET.get('projet_id')
        audit_id = request.GET.get('audit_id')

        queryset = JournalActivite.objects.select_related('utilisateur', 'projet', 'audit').all()
        if user_id:
            queryset = queryset.filter(utilisateur_id=user_id)
        if project_id:
            queryset = queryset.filter(projet_id=project_id)
        if audit_id:
            queryset = queryset.filter(audit_id=audit_id)

        logs_data = []
        for log in queryset:
            logs_data.append({
                'id': str(log.id),
                'utilisateur': {
                    'id': str(log.utilisateur.id),
                    'nom': log.utilisateur.nom,
                    'email': log.utilisateur.email
                },
                'projet': {'id': str(log.projet.id), 'nom': log.projet.nom} if log.projet else None,
                'audit': {'id': str(log.audit.id), 'cible': log.audit.cible.valeur} if log.audit else None,
                'action': log.action,
                'ressource': log.ressource,
                'details': log.details,
                'adresseIP': log.adresseIP,
                'dateAction': log.dateAction.isoformat()
            })
        return json_response({'logs': logs_data, 'total': len(logs_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            utilisateur_id = data.get('utilisateur_id')
            action = data.get('action')
            ressource = data.get('ressource')
            details = data.get('details', '')
            adresseIP = data.get('adresseIP', request.META.get('REMOTE_ADDR', '127.0.0.1'))
            projet_id = data.get('projet_id')
            audit_id = data.get('audit_id')

            if not utilisateur_id or not action or not ressource:
                return json_response({'error': 'Champs utilisateur_id, action et ressource obligatoires.'}, status=400)

            utilisateur = Utilisateur.objects.get(id=utilisateur_id)
            projet = Projet.objects.get(id=projet_id) if projet_id else None
            audit = Audit.objects.get(id=audit_id) if audit_id else None

            log = JournalActivite.enregistrer(
                utilisateur=utilisateur,
                action=action,
                ressource=ressource,
                details=details,
                adresseIP=adresseIP,
                projet=projet,
                audit=audit
            )

            return json_response({
                'message': 'Activité journalisée avec succès.',
                'log': {
                    'id': str(log.id),
                    'action': log.action,
                    'ressource': log.ressource,
                    'dateAction': log.dateAction.isoformat()
                }
            }, status=201)
        except Utilisateur.DoesNotExist:
            return json_response({'error': 'Utilisateur introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def log_detail_view(request, log_id):
    """GET: Detail. DELETE: Delete log entry."""
    try:
        log = JournalActivite.objects.select_related('utilisateur', 'projet', 'audit').get(id=log_id)
    except JournalActivite.DoesNotExist:
        return json_response({'error': 'Journal d\'activité introuvable.'}, status=404)

    if request.method == 'GET':
        return json_response({
            'id': str(log.id),
            'utilisateur': {
                'id': str(log.utilisateur.id),
                'nom': log.utilisateur.nom,
                'email': log.utilisateur.email
            },
            'projet': {'id': str(log.projet.id), 'nom': log.projet.nom} if log.projet else None,
            'audit': {'id': str(log.audit.id), 'cible': log.audit.cible.valeur} if log.audit else None,
            'action': log.action,
            'ressource': log.ressource,
            'details': log.details,
            'adresseIP': log.adresseIP,
            'dateAction': log.dateAction.isoformat()
        })

    elif request.method == 'DELETE':
        log.delete()
        return json_response({'message': 'Journal supprimé avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)
