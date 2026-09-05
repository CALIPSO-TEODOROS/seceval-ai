import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Notification, CanalNotification
from audits.models import Audit
from users.models import Utilisateur
from logs_app.models import JournalActivite


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def notifications_list_create_view(request):
    """GET: List notifications. POST: Create and optionally send a notification."""
    if request.method == 'GET':
        destinataire_id = request.GET.get('destinataire_id')
        queryset = Notification.objects.select_related('destinataire', 'audit').all().order_by('-dateCreation')
        if destinataire_id:
            queryset = queryset.filter(destinataire_id=destinataire_id)

        notifs_data = []
        for n in queryset:
            notifs_data.append({
                'id': str(n.id),
                'destinataire': {'id': str(n.destinataire.id), 'nom': n.destinataire.nom, 'email': n.destinataire.email} if n.destinataire else {'id': None, 'nom': 'Système', 'email': 'systeme@seceval.io'},
                'audit': {'id': str(n.audit.id), 'cible': n.audit.cible.valeur} if (n.audit and n.audit.cible) else None,
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
        return json_response({
            'error': "L'envoi manuel de notifications est désactivé. Les notifications d'audit sont envoyées automatiquement à la fin de chaque audit avec le rapport en pièce jointe."
        }, status=403)

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
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="RENVOI_NOTIFICATION",
            ressource=n.destinataire.email,
            details=f"Renvoi de la notification [{n.canal}] '{n.sujet}' à {n.destinataire.email}.",
            audit=n.audit
        )
        return json_response({
            'message': f'Notification envoyée via {n.get_canal_display()}.',
            'statut': n.statut,
            'dateEnvoi': n.dateEnvoi.isoformat()
        })
    except Notification.DoesNotExist:
        return json_response({'error': 'Notification introuvable.'}, status=404)
