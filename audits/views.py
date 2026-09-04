import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import (
    Audit,
    PlanAudit,
    EtapeAudit,
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
                webhookN8nUrl=webhook_n8n_url
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
    """GET: Detail with Plan and Etapes. DELETE: Delete audit."""
    try:
        audit = Audit.objects.select_related('projet', 'cible', 'lancePar').get(id=audit_id)
    except Audit.DoesNotExist:
        return json_response({'error': 'Audit introuvable.'}, status=404)

    if request.method == 'GET':
        plan_data = None
        if hasattr(audit, 'plan'):
            plan = audit.plan
            etapes_data = []
            for e in plan.etapes.all():
                etapes_data.append({
                    'id': str(e.id),
                    'ordre': e.ordre,
                    'nom': e.nom,
                    'statut': e.statut,
                    'statut_display': e.get_statut_display(),
                    'dateDebut': e.dateDebut.isoformat() if e.dateDebut else None,
                    'dateFin': e.dateFin.isoformat() if e.dateFin else None
                })
            plan_data = {
                'id': str(plan.id),
                'description': plan.description,
                'dateGeneration': plan.dateGeneration.isoformat(),
                'etapes': etapes_data
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
            'resultatBrutN8n': audit.resultatBrutN8n or {},
            'scoreSecurite': audit.scoreSecurite,



            'progression': audit.progression,
            'dateCreation': audit.dateCreation.isoformat(),
            'dateDebut': audit.dateDebut.isoformat() if audit.dateDebut else None,
            'dateFin': audit.dateFin.isoformat() if audit.dateFin else None,
            'plan': plan_data
        })


    elif request.method == 'DELETE':
        audit.delete()
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


        # Enregistrer un rapport d'évaluation si du contenu texte est fourni par n8n
        if rapport_text:
            from reports.models import Rapport, FormatRapport, StatutRapport
            Rapport.objects.create(
                titre=f"Rapport Automatise n8n - {audit.titre or audit.cible.valeur}",
                audit=audit,
                format=FormatRapport.HTML,
                statut=StatutRapport.PUBLIE,
                cheminFichier=rapport_text[:255],
                scoreFinal=audit.scoreSecurite
            )


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


