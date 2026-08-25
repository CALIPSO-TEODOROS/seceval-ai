import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Notification, CanalNotification
from audits.models import Audit
from users.models import Utilisateur


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def notifications_list_create_view(request):
    """GET: List notifications. POST: Create and optionally send a notification."""
    if request.method == 'GET':
        destinataire_id = request.GET.get('destinataire_id')
        queryset = Notification.objects.select_related('destinataire', 'audit').all()
        if destinataire_id:
            queryset = queryset.filter(destinataire_id=destinataire_id)

        notifs_data = []
        for n in queryset:
            notifs_data.append({
                'id': str(n.id),
                'destinataire': {'id': str(n.destinataire.id), 'nom': n.destinataire.nom, 'email': n.destinataire.email},
                'audit': {'id': str(n.audit.id), 'cible': n.audit.cible.valeur} if n.audit else None,
                'canal': n.canal,
                'canal_display': n.get_canal_display(),
                'sujet': n.sujet,
                'message': n.message,
                'statut': n.statut,
                'dateCreation': n.dateCreation.isoformat(),
                'dateEnvoi': n.dateEnvoi.isoformat() if n.dateEnvoi else None
            })
        return json_response({'notifications': notifs_data, 'total': len(notifs_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            destinataire_id = data.get('destinataire_id')
            sujet = data.get('sujet')
            message = data.get('message')
            canal = data.get('canal', CanalNotification.EMAIL)
            audit_id = data.get('audit_id')

            if not destinataire_id or not sujet or not message:
                return json_response({'error': 'Champs destinataire_id, sujet et message obligatoires.'}, status=400)

            destinataire = Utilisateur.objects.get(id=destinataire_id)
            audit = Audit.objects.get(id=audit_id) if audit_id else None

            notif = Notification.objects.create(
                destinataire=destinataire,
                audit=audit,
                canal=canal,
                sujet=sujet,
                message=message,
                statut="EN_ATTENTE"
            )

            # Auto-envoyer
            notif.envoyer()

            return json_response({
                'message': 'Notification créée et envoyée avec succès.',
                'notification': {
                    'id': str(notif.id),
                    'sujet': notif.sujet,
                    'canal': notif.canal,
                    'statut': notif.statut,
                    'dateEnvoi': notif.dateEnvoi.isoformat() if notif.dateEnvoi else None
                }
            }, status=201)
        except Utilisateur.DoesNotExist:
            return json_response({'error': 'Destinataire introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def notification_detail_view(request, notification_id):
    """GET: Detail. DELETE: Delete notification."""
    try:
        n = Notification.objects.select_related('destinataire', 'audit').get(id=notification_id)
    except Notification.DoesNotExist:
        return json_response({'error': 'Notification introuvable.'}, status=404)

    if request.method == 'GET':
        return json_response({
            'id': str(n.id),
            'destinataire': {'id': str(n.destinataire.id), 'nom': n.destinataire.nom, 'email': n.destinataire.email},
            'audit': {'id': str(n.audit.id), 'cible': n.audit.cible.valeur} if n.audit else None,
            'canal': n.canal,
            'canal_display': n.get_canal_display(),
            'sujet': n.sujet,
            'message': n.message,
            'statut': n.statut,
            'dateCreation': n.dateCreation.isoformat(),
            'dateEnvoi': n.dateEnvoi.isoformat() if n.dateEnvoi else None
        })

    elif request.method == 'DELETE':
        n.delete()
        return json_response({'message': 'Notification supprimée avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def notification_envoyer_view(request, notification_id):
    """POST: Action envoyer()."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)
    try:
        n = Notification.objects.get(id=notification_id)
        n.envoyer()
        return json_response({
            'message': f'Notification envoyée via {n.get_canal_display()}.',
            'statut': n.statut,
            'dateEnvoi': n.dateEnvoi.isoformat()
        })
    except Notification.DoesNotExist:
        return json_response({'error': 'Notification introuvable.'}, status=404)
