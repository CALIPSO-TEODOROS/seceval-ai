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
        return json_response({'error': "L'enregistrement manuel des événements d'activité est désactivé. Le journal d'activité est généré automatiquement par le système."}, status=403)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def log_detail_view(request, log_id):
    """GET: Detail."""
    try:
        log = JournalActivite.objects.select_related('utilisateur', 'projet', 'audit').get(id=log_id)
    except JournalActivite.DoesNotExist:
        return json_response({'error': 'Journal d\'activité introuvable.'}, status=404)

    if request.method == 'GET':
        user_info = None
        if log.utilisateur:
            user_info = {
                'id': str(log.utilisateur.id),
                'nom': log.utilisateur.nom,
                'email': log.utilisateur.email
            }
        return json_response({
            'id': str(log.id),
            'utilisateur': user_info,
            'projet': {'id': str(log.projet.id), 'nom': log.projet.nom} if log.projet else None,
            'audit': {'id': str(log.audit.id), 'cible': log.audit.cible.valeur} if log.audit else None,
            'action': log.action,
            'ressource': log.ressource,
            'details': log.details,
            'adresseIP': log.adresseIP,
            'dateAction': log.dateAction.isoformat()
        })

    elif request.method == 'DELETE':
        return json_response({'error': "La suppression des journaux d'activité est interdite pour des raisons d'intégrité et de traçabilité."}, status=403)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)
