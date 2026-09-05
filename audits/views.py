import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .models import (
    Audit,
    PlanAudit,
    EtapeAudit,
    ExecutionAudit,
    TypeAudit,
    StatutAudit,
    StatutExecution
)
from projects.models import Projet, Cible


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def audits_list_create_view(request):
    """GET: List all audits. POST: Create a new audit."""
    if request.method == 'GET':
        audits = Audit.objects.select_related('projet', 'cible', 'lancePar').all()
        audits_data = []
        for a in audits:
            audits_data.append({
                'id': str(a.id),
                'titre': a.titre or f"Audit {a.get_type_display()} - {a.cible.valeur}",
                'contexte': a.contexte,
                'projet': {'id': str(a.projet.id), 'nom': a.projet.nom},
                'cible': {'id': str(a.cible.id), 'valeur': a.cible.valeur, 'type': a.cible.type},
                'lancePar': a.lancePar.nom if a.lancePar else 'Système / Anonyme',
                'type': a.type,
                'type_display': a.get_type_display(),
                'statut': a.statut,
                'statut_display': a.get_statut_display(),
                'typePlanification': a.typePlanification,
                'typePlanification_display': a.get_typePlanification_display(),
                'frequence': a.frequence,
                'frequence_display': a.get_frequence_display(),
                'heureExecution': a.heureExecution.strftime('%H:%M') if a.heureExecution else None,
                'prochaineExecution': a.prochaineExecution.isoformat() if a.prochaineExecution else None,
                'dateDernierLancement': a.dateDernierLancement.isoformat() if a.dateDernierLancement else None,
                'webhookN8nUrl': a.webhookN8nUrl,
                'emailsNotification': a.emailsNotification,
                'resultatBrutN8n': a.resultatBrutN8n or {},
                'scoreSecurite': a.scoreSecurite,
                'progression': a.progression,
                'dateCreation': a.dateCreation.isoformat(),
                'dateDebut': a.dateDebut.isoformat() if a.dateDebut else None,
                'dateFin': a.dateFin.isoformat() if a.dateFin else None
            })


        return json_response({'audits': audits_data, 'total': len(audits_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            projet_id = data.get('projet_id')
            cible_id = data.get('cible_id')
            audit_type = data.get('type', TypeAudit.STANDARD)
            titre = data.get('titre', '').strip()
            contexte = data.get('contexte', '').strip()
            type_planification = data.get('typePlanification', 'UNIQUE')
            frequence = data.get('frequence', 'AUCUNE')
            heure_execution_str = data.get('heureExecution')
            prochaine_exec = data.get('prochaineExecution')
            webhook_n8n_url = data.get('webhookN8nUrl', '').strip()
            emails_notification = data.get('emailsNotification', '').strip()

            if not projet_id or not cible_id:
                return json_response({'error': 'Le projet_id et la cible_id sont obligatoires.'}, status=400)

            projet = Projet.objects.get(id=projet_id)
            cible = Cible.objects.get(id=cible_id)

            if not titre:
                type_display = dict(TypeAudit.choices).get(audit_type, audit_type)
                titre = f"Audit {type_display} - {cible.valeur}"

            user = request.user if request.user.is_authenticated else None

            heure_exec = None
            if heure_execution_str:
                try:
                    parts = heure_execution_str.split(':')
                    heure_exec = timezone.datetime.strptime(f"{parts[0]}:{parts[1]}", "%H:%M").time()
                except Exception:
                    heure_exec = None

            audit = Audit.objects.create(
                titre=titre,
                contexte=contexte,
                projet=projet,
                cible=cible,
                lancePar=user,
                type=audit_type,
                statut=StatutAudit.EN_ATTENTE,
                typePlanification=type_planification,
                frequence=frequence,
                heureExecution=heure_exec,
                prochaineExecution=prochaine_exec,
                webhookN8nUrl=webhook_n8n_url,
                emailsNotification=emails_notification
            )

            from logs_app.models import JournalActivite
            JournalActivite.enregistrer_depuis_requete(
                request,
                action="CREATION_AUDIT",
                ressource=cible.valeur,
                details=f"Création de l'audit '{audit.titre}' ({audit.get_type_display()}) sur {cible.valeur}.",
                projet=projet,
                audit=audit
            )

            return json_response({
                'message': 'Audit de sécurité créé avec succès.',
                'audit': {
                    'id': str(audit.id),
                    'titre': audit.titre,
                    'contexte': audit.contexte,
                    'type': audit.type,
                    'statut': audit.statut,
                    'typePlanification': audit.typePlanification,
                    'frequence': audit.frequence,
                    'heureExecution': audit.heureExecution.strftime('%H:%M') if audit.heureExecution else None,
                    'webhookN8nUrl': audit.webhookN8nUrl,
                    'dateCreation': audit.dateCreation.isoformat()
                }
            }, status=201)

        except Projet.DoesNotExist:
            return json_response({'error': 'Projet introuvable.'}, status=404)
        except Cible.DoesNotExist:
            return json_response({'error': 'Cible introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)



@csrf_exempt
def audit_detail_view(request, audit_id):
    """GET: Detail. DELETE: Delete audit."""
    try:
        audit = Audit.objects.select_related('projet', 'cible', 'lancePar').get(id=audit_id)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)

    if request.method == 'GET':
        plan_data = None
        if hasattr(audit, 'plan') and audit.plan:
            etapes = []
            for e in audit.plan.etapes.all():
                etapes.append({
                    'id': str(e.id),
                    'ordre': e.ordre,
                    'nom': e.nom,
                    'description': e.description,
                    'commandesSimulees': e.commandesSimulees,
                    'statut': e.statut,
                    'statut_display': e.get_statut_display(),
                    'dateDebut': e.dateDebut.isoformat() if e.dateDebut else None,
                    'dateFin': e.dateFin.isoformat() if e.dateFin else None
                })
            plan_data = {
                'id': str(audit.plan.id),
                'nom': audit.plan.nom,
                'statutGlobal': audit.plan.statutGlobal,
                'statutGlobal_display': audit.plan.get_statutGlobal_display(),
                'etapes': etapes
            }

        return json_response({
            'id': str(audit.id),
            'titre': audit.titre or f"Audit {audit.get_type_display()} - {audit.cible.valeur}",
            'contexte': audit.contexte,
            'projet': {'id': str(audit.projet.id), 'nom': audit.projet.nom},
            'cible': {'id': str(audit.cible.id), 'valeur': audit.cible.valeur, 'type': audit.cible.type},
            'lancePar': audit.lancePar.nom if audit.lancePar else 'Système / Anonyme',
            'type': audit.type,
            'type_display': audit.get_type_display(),
            'statut': audit.statut,
            'statut_display': audit.get_statut_display(),
            'typePlanification': audit.typePlanification,
            'typePlanification_display': audit.get_typePlanification_display(),
            'frequence': audit.frequence,
            'frequence_display': audit.get_frequence_display(),
            'heureExecution': audit.heureExecution.strftime('%H:%M') if audit.heureExecution else None,
            'prochaineExecution': audit.prochaineExecution.isoformat() if audit.prochaineExecution else None,
            'dateDernierLancement': audit.dateDernierLancement.isoformat() if audit.dateDernierLancement else None,
            'webhookN8nUrl': audit.webhookN8nUrl,
            'emailsNotification': audit.emailsNotification,
            'resultatBrutN8n': audit.resultatBrutN8n or {},
            'scoreSecurite': audit.scoreSecurite,

            'progression': audit.progression,
            'dateCreation': audit.dateCreation.isoformat(),
            'dateDebut': audit.dateDebut.isoformat() if audit.dateDebut else None,
            'dateFin': audit.dateFin.isoformat() if audit.dateFin else None,
            'plan': plan_data
        })

    elif request.method == 'DELETE':
        from logs_app.models import JournalActivite
        cible_valeur = audit.cible.valeur
        audit_titre = audit.titre or audit.cible.valeur
        proj = audit.projet
        audit.delete()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="SUPPRESSION_AUDIT",
            ressource=cible_valeur,
            details=f"Suppression définitive de l'audit '{audit_titre}'.",
            projet=proj
        )
        return json_response({'message': 'Audit supprimé avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def audit_demarrer_view(request, audit_id):
    """POST: Lancer un audit (demarrer())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.get(id=audit_id)
        audit.demarrer()
        from logs_app.models import JournalActivite
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="DEMARRAGE_AUDIT",
            ressource=audit.cible.valeur,
            details=f"Démarrage de l'audit '{audit.titre or audit.get_type_display()}' sur {audit.cible.valeur}.",
            projet=audit.projet,
            audit=audit
        )
        return json_response({
            'message': f'Audit {audit.get_type_display()} démarré avec succès sur {audit.cible.valeur}.',
            'audit': {
                'id': str(audit.id),
                'statut': audit.statut,
                'dateDebut': audit.dateDebut.isoformat()
            }
        })
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def audit_pause_view(request, audit_id):
    """POST: Mettre en pause un audit (mettreEnPause())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.get(id=audit_id)
        audit.mettreEnPause()
        from logs_app.models import JournalActivite
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="MISE_EN_PAUSE_AUDIT",
            ressource=audit.cible.valeur,
            details=f"Mise en pause de l'audit '{audit.titre or audit.cible.valeur}'.",
            projet=audit.projet,
            audit=audit
        )
        return json_response({'message': 'Audit mis en pause.', 'statut': audit.statut})
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)


@csrf_exempt
def audit_arreter_view(request, audit_id):
    """POST: Arrêter/annuler un audit (arreter())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.get(id=audit_id)
        audit.arreter()
        from logs_app.models import JournalActivite
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="ARRET_AUDIT",
            ressource=audit.cible.valeur,
            details=f"Arrêt/annulation de l'audit '{audit.titre or audit.cible.valeur}'.",
            projet=audit.projet,
            audit=audit
        )
        return json_response({'message': 'Audit arrêté / annulé.', 'statut': audit.statut})
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)


@csrf_exempt
def audit_terminer_view(request, audit_id):
    """POST: Terminer un audit et calculer le score (terminer(), calculerScore())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.get(id=audit_id)
        audit.terminer()
        send_audit_completion_notifications(audit)
        return json_response({
            'message': 'Audit terminé avec succès.',
            'audit': {
                'id': str(audit.id),
                'statut': audit.statut,
                'scoreSecurite': audit.scoreSecurite,
                'progression': audit.progression,
                'dateFin': audit.dateFin.isoformat()
            }
        })
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def audit_etape_update_view(request, etape_id):
    """POST: Exécuter ou mettre à jour le statut d'une EtapeAudit."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        statut = data.get('statut')

        if statut not in StatutExecution.values:
            return json_response({'error': f'Statut invalide. Permis: {StatutExecution.values}'}, status=400)

        etape = EtapeAudit.objects.get(id=etape_id)
        etape.statut = statut

        if statut == StatutExecution.RUNNING and not etape.dateDebut:
            etape.dateDebut = timezone.now()
        elif statut in [StatutExecution.COMPLETED, StatutExecution.FAILED, StatutExecution.TIMEOUT, StatutExecution.CANCELLED]:
            etape.dateFin = timezone.now()

        etape.save()

        # Update audit progression
        audit = etape.plan.audit
        total_etapes = audit.plan.etapes.count()
        completed_etapes = audit.plan.etapes.filter(statut__in=[StatutExecution.COMPLETED, StatutExecution.FAILED]).count()
        if total_etapes > 0:
            audit.progression = int((completed_etapes / total_etapes) * 100)
            audit.calculerScore()
            audit.save(update_fields=['progression', 'scoreSecurite'])

        return json_response({
            'message': f'Étape "{etape.nom}" mise à jour avec succès.',
            'etape': {
                'id': str(etape.id),
                'ordre': etape.ordre,
                'nom': etape.nom,
                'statut': etape.statut,
                'statut_display': etape.get_statut_display()
            },
            'audit_progression': audit.progression,
            'audit_score': audit.scoreSecurite
        })
    except EtapeAudit.DoesNotExist:
        return json_response({'error': 'Étape introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


def send_audit_completion_notifications(audit, rapport_obj=None, filepath=None):
    """
    Envoie automatiquement un email avec le rapport d'audit en pièce jointe 
    aux adresses emails configurées dans audit.emailsNotification (ou à l'utilisateur qui a lancé l'audit).
    Crée également l'enregistrement de notification correspondant en base.
    """
    from django.core.mail import EmailMessage
    from notifications_app.models import Notification, CanalNotification
    from users.models import Utilisateur

    recipients = []
    if audit.emailsNotification:
        raw_list = audit.emailsNotification.replace(';', ',').split(',')
        recipients = [e.strip() for e in raw_list if e.strip()]

    if not recipients and audit.lancePar and audit.lancePar.email:
        recipients = [audit.lancePar.email]

    if not recipients:
        first_user = Utilisateur.objects.first()
        if first_user and first_user.email:
            recipients = [first_user.email]
        else:
            recipients = [getattr(settings, 'DEFAULT_FROM_EMAIL', 'brandon.follah@saintjeaningenieur.org')]

    titre_audit = audit.titre or f"Audit {audit.get_type_display()} - {audit.cible.valeur}"
    subject = f"[SecEval AI] Notification d'audit terminé : {titre_audit}"

    date_crea_str = audit.dateCreation.strftime('%d/%m/%Y %H:%M') if audit.dateCreation else 'N/A'
    date_fin_str = audit.dateFin.strftime('%d/%m/%Y %H:%M') if audit.dateFin else timezone.now().strftime('%d/%m/%Y %H:%M')
    cible_valeur = audit.cible.valeur if audit.cible else 'N/A'
    cible_type = audit.cible.get_type_display() if audit.cible else 'N/A'
    type_display = audit.get_type_display() if hasattr(audit, 'get_type_display') else audit.type

    body_text = f"""Bonjour,

L'audit de sécurité SecEval AI est terminé. Retrouvez ci-dessous les informations d'identification et le rapport complet.

--- INFORMATIONS DE L'AUDIT ---
- ID de l'audit : {audit.id}
- Titre : {titre_audit}
- Cible : {cible_valeur} ({cible_type})
- Type d'audit : {type_display}
- Score de sécurité : {audit.scoreSecurite}/100
- Statut : {audit.get_statut_display()}
- Date de création : {date_crea_str}
- Date de fin : {date_fin_str}
- Destinataires : {', '.join(recipients)}

Le rapport d'évaluation est joint à ce courrier électronique.

Cordialement,
L'équipe SecEval AI
"""

    try:
        email = EmailMessage(
            subject=subject,
            body=body_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'brandon.follah@saintjeaningenieur.org'),
            to=recipients
        )
        if filepath and os.path.exists(filepath):
            email.attach_file(filepath)
        email.send(fail_silently=True)
    except Exception as e:
        print(f"Erreur lors de l'envoi du mail de notification d'audit: {e}")

    destinataire_user = audit.lancePar or Utilisateur.objects.first()
    if destinataire_user:
        try:
            Notification.objects.create(
                audit=audit,
                destinataire=destinataire_user,
                canal=CanalNotification.EMAIL,
                sujet=subject,
                message=f"Rapport d'audit '{titre_audit}' envoyé à : {', '.join(recipients)}. Score : {audit.scoreSecurite}/100.",
                statut="ENVOYE",
                dateEnvoi=timezone.now()
            )
        except Exception as e:
            print(f"Erreur lors de la création de la notification: {e}")


@csrf_exempt
def audit_callback_n8n_view(request, audit_id):
    """
    POST/GET: Webhook Callback appelé par n8n lorsque le traitement de l'agent IA est terminé.
    Met à jour le statut, le score, la progression et crée le rapport d'audit dans SecEval AI.
    """
    if request.method not in ['POST', 'GET']:
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        audit = Audit.objects.get(id=audit_id)

        data = {}
        if request.method == 'GET':
            data = request.GET.dict()
        else:
            if request.body:
                try:
                    data = json.loads(request.body.decode('utf-8'))
                except Exception:
                    data = request.POST.dict()
            if not data:
                data = request.POST.dict()


        rapport_text = data.get('rapport') or data.get('output') or data.get('result') or data.get('text') or ''
        score = float(data.get('scoreSecurite', 85.0))
        progression = int(data.get('progression', 100))

        audit.statut = StatutAudit.TERMINE
        audit.scoreSecurite = min(100.0, max(0.0, score))
        audit.progression = min(100, max(0, progression))
        audit.dateFin = timezone.now()
        audit.resultatBrutN8n = data
        audit.save()

        # Met à jour la dernière exécution ou en crée une nouvelle
        latest_exec = audit.executions.filter(statut=StatutAudit.EN_COURS).order_by('-dateExecution').first()
        if not latest_exec:
            latest_exec = ExecutionAudit.objects.create(audit=audit, statut=StatutAudit.EN_COURS)
        
        latest_exec.statut = StatutAudit.TERMINE
        latest_exec.scoreSecurite = audit.scoreSecurite
        latest_exec.resultatBrutN8n = data
        latest_exec.rapportText = rapport_text
        latest_exec.dateFin = timezone.now()
        latest_exec.save()

        # Enregistrer un rapport d'évaluation si du contenu texte est fourni par n8n
        new_rapport = None
        filepath = None
        if rapport_text:
            from reports.models import Rapport, FormatRapport, StatutRapport
            dir_path = os.path.join(settings.BASE_DIR, 'media', 'reports')
            os.makedirs(dir_path, exist_ok=True)
            new_rapport = Rapport.objects.create(
                titre=f"Rapport Automatise n8n - {audit.titre or audit.cible.valeur}",
                audit=audit,
                format=FormatRapport.HTML,
                statut=StatutRapport.PUBLIE,
                scoreFinal=audit.scoreSecurite
            )
            filename = f"rapport_n8n_{audit.id}_{new_rapport.id}.html"
            filepath = os.path.join(dir_path, filename)
            html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{new_rapport.titre}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; background: #0f172a; color: #f8fafc; }}
pre {{ background: #1e293b; padding: 15px; border-radius: 8px; overflow-x: auto; }}
h1, h2, h3 {{ color: #38bdf8; }}
hr {{ border-color: #334155; }}
</style>
</head>
<body>
<div>{rapport_text.replace('\n', '<br>')}</div>
</body>
</html>"""
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            new_rapport.cheminFichier = filepath
            new_rapport.save(update_fields=['cheminFichier'])

        # Envoi automatique de notification par email avec rapport
        send_audit_completion_notifications(audit, new_rapport, filepath)


        # Enregistrer l'activité dans le journal
        from logs_app.models import JournalActivite
        if audit.lancePar:
            JournalActivite.enregistrer(
                utilisateur=audit.lancePar,
                action="TRAITEMENT_N8N_TERMINE",
                ressource=audit.cible.valeur,
                details=f"n8n AI Agent a finalisé l'audit '{audit.titre}' sur {audit.cible.valeur}.",
                projet=audit.projet,
                audit=audit
            )


        return json_response({
            'message': 'Résultat du traitement n8n enregistré avec succès dans SecEval AI.',
            'audit': {
                'id': str(audit.id),
                'statut': audit.statut,
                'scoreSecurite': audit.scoreSecurite,
                'progression': audit.progression,
                'dateFin': audit.dateFin.isoformat()
            }
        })
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


def audit_historique_view(request, audit_id):
    """
    GET: Renvoie l'historique chronologique de toutes les exécutions passées d'un audit récurrent/répétitif.
    """
    try:
        audit = Audit.objects.get(id=audit_id)
        executions = audit.executions.all().order_by('-dateExecution')
        data = []
        for idx, ex in enumerate(executions, start=1):
            data.append({
                'id': str(ex.id),
                'num_run': len(executions) - idx + 1,
                'dateExecution': ex.dateExecution.isoformat(),
                'dateExecution_display': ex.dateExecution.strftime('%d/%m/%Y %H:%M:%S'),
                'dateFin': ex.dateFin.strftime('%d/%m/%Y %H:%M:%S') if ex.dateFin else 'En cours',
                'statut': ex.statut,
                'statut_display': ex.get_statut_display(),
                'scoreSecurite': ex.scoreSecurite,
                'has_rapport': bool(ex.rapportText or ex.resultatBrutN8n),
                'resultatBrutN8n': ex.resultatBrutN8n or {}
            })
        return json_response({
            'audit_id': str(audit.id),
            'titre': audit.titre,
            'typePlanification': audit.typePlanification,
            'frequence_display': audit.get_frequence_display(),
            'executions': data,
            'total': len(data)
        })
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)


def execution_rapport_page_view(request, execution_id):
    """
    GET: Vue HTML dédiée pleine page du rapport pour une exécution d'audit récurrente spécifique.
    """
    from django.shortcuts import render
    try:
        execution = ExecutionAudit.objects.select_related('audit', 'audit__projet', 'audit__cible').get(id=execution_id)
        raw_data = execution.resultatBrutN8n or {}
        report_text = execution.rapportText or raw_data.get('rapport') or raw_data.get('output') or raw_data.get('result') or raw_data.get('text') or ''
        
        return render(request, 'audits/rapport_detail.html', {
            'audit': execution.audit,
            'execution': execution,
            'raw_data_json': json.dumps(raw_data, indent=2, ensure_ascii=False),
            'report_text': report_text
        })
    except ExecutionAudit.DoesNotExist:
        return json_response({'error': 'Exécution d\'audit introuvable.'}, status=404)


def audit_rapport_page_view(request, audit_id):
    """
    GET: Vue HTML dédiée pleine page du rapport d'audit pour lecture et impression PDF.
    """
    from django.shortcuts import render
    try:
        audit = Audit.objects.select_related('projet', 'cible', 'lancePar').get(id=audit_id)
        raw_data = audit.resultatBrutN8n or {}
        report_text = raw_data.get('rapport') or raw_data.get('output') or raw_data.get('result') or raw_data.get('text') or audit.contexte or ''
        
        return render(request, 'audits/rapport_detail.html', {
            'audit': audit,
            'raw_data_json': json.dumps(raw_data, indent=2, ensure_ascii=False),
            'report_text': report_text
        })
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)
