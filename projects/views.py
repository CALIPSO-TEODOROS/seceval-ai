import json
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.utils import timezone
from .models import (
    Projet,
    Cible,
    AutorisationCible,
    StatutProjet,
    TypeCible,
    Environnement,
    StatutCible
)
from logs_app.models import JournalActivite


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
def projects_list_create_view(request):
    """GET: List all projects. POST: Create a new project (creer())."""
    if request.method == 'GET':
        projects = Projet.objects.all()
        projects_data = []
        for p in projects:
            projects_data.append({
                'id': str(p.id),
                'nom': p.nom,
                'organisation': p.organisation,
                'description': p.description,
                'statut': p.statut,
                'statut_display': p.get_statut_display(),
                'dateCreation': p.dateCreation.isoformat(),
                'dateArchivage': p.dateArchivage.isoformat() if p.dateArchivage else None,
                'cibles_count': p.cibles.count()
            })
        return json_response({'projects': projects_data, 'total': len(projects_data)})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            nom = data.get('nom')
            organisation = data.get('organisation')
            description = data.get('description', '')
            statut = data.get('statut', StatutProjet.ACTIF)

            if not nom or not organisation:
                return json_response({'error': 'Le nom et l\'organisation sont obligatoires.'}, status=400)

            project = Projet.creer(
                nom=nom,
                organisation=organisation,
                description=description,
                statut=statut
            )

            JournalActivite.enregistrer_depuis_requete(
                request,
                action="CREATION_PROJET",
                ressource=project.nom,
                details=f"Création du projet '{project.nom}' (Organisation: {project.organisation}).",
                projet=project
            )

            return json_response({
                'message': 'Projet créé avec succès.',
                'project': {
                    'id': str(project.id),
                    'nom': project.nom,
                    'organisation': project.organisation,
                    'statut': project.statut,
                    'dateCreation': project.dateCreation.isoformat()
                }
            }, status=201)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def project_detail_view(request, project_id):
    """GET, PUT/PATCH (modifier()), DELETE (supprimer())."""
    try:
        project = Projet.objects.get(id=project_id)
    except Projet.DoesNotExist:
        return json_response({'error': 'Projet non trouvé.'}, status=404)

    if request.method == 'GET':
        cibles_data = []
        for c in project.cibles.all():
            cibles_data.append({
                'id': str(c.id),
                'valeur': c.valeur,
                'type': c.type,
                'type_display': c.get_type_display(),
                'environnement': c.environnement,
                'environnement_display': c.get_environnement_display(),
                'statut': c.statut,
                'statut_display': c.get_statut_display(),
                'dateAjout': c.dateAjout.isoformat()
            })

        return json_response({
            'id': str(project.id),
            'nom': project.nom,
            'organisation': project.organisation,
            'description': project.description,
            'statut': project.statut,
            'statut_display': project.get_statut_display(),
            'dateCreation': project.dateCreation.isoformat(),
            'dateArchivage': project.dateArchivage.isoformat() if project.dateArchivage else None,
            'cibles': cibles_data
        })

    elif request.method in ['PUT', 'PATCH']:
        try:
            data = json.loads(request.body)
            project.modifier(
                nom=data.get('nom'),
                description=data.get('description'),
                organisation=data.get('organisation'),
                statut=data.get('statut')
            )
            JournalActivite.enregistrer_depuis_requete(
                request,
                action="MODIFICATION_PROJET",
                ressource=project.nom,
                details=f"Modification des informations du projet '{project.nom}'.",
                projet=project
            )
            return json_response({
                'message': 'Projet mis à jour avec succès.',
                'project': {
                    'id': str(project.id),
                    'nom': project.nom,
                    'organisation': project.organisation,
                    'statut': project.statut
                }
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        nom_proj = project.nom
        project.supprimer()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="SUPPRESSION_PROJET",
            ressource=nom_proj,
            details=f"Suppression définitive du projet '{nom_proj}'."
        )
        return json_response({'message': 'Projet supprimé avec succès.'})

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def project_archive_view(request, project_id):
    """POST: Archiver un projet (archiver())."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        project = Projet.objects.get(id=project_id)
        project.archiver()
        JournalActivite.enregistrer_depuis_requete(
            request,
            action="ARCHIVAGE_PROJET",
            ressource=project.nom,
            details=f"Archivage du projet '{project.nom}'.",
            projet=project
        )
        return json_response({
            'message': f'Le projet {project.nom} a été archivé avec succès.',
            'project': {
                'id': str(project.id),
                'nom': project.nom,
                'statut': project.statut,
                'dateArchivage': project.dateArchivage.isoformat()
            }
        })
    except Projet.DoesNotExist:
        return json_response({'error': 'Projet non trouvé.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def project_cibles_view(request, project_id):
    """GET: List cibles for project. POST: Add a new Cible."""
    try:
        project = Projet.objects.get(id=project_id)
    except Projet.DoesNotExist:
        return json_response({'error': 'Projet non trouvé.'}, status=404)

    if request.method == 'GET':
        cibles = project.cibles.all()
        cibles_data = []
        for c in cibles:
            cibles_data.append({
                'id': str(c.id),
                'valeur': c.valeur,
                'type': c.type,
                'type_display': c.get_type_display(),
                'environnement': c.environnement,
                'environnement_display': c.get_environnement_display(),
                'statut': c.statut,
                'statut_display': c.get_statut_display(),
                'dateAjout': c.dateAjout.isoformat()
            })
        return json_response({'cibles': cibles_data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            valeur = data.get('valeur')
            target_type = data.get('type', TypeCible.URL)
            environnement = data.get('environnement', Environnement.TEST)

            if not valeur:
                return json_response({'error': 'La valeur de la cible est obligatoire.'}, status=400)

            cible = Cible.objects.create(
                projet=project,
                valeur=valeur,
                type=target_type,
                environnement=environnement,
                statut=StatutCible.EN_ATTENTE
            )

            # Auto-verify accessibility
            accessible, acc_msg = cible.verifierAccessibilite()

            JournalActivite.enregistrer_depuis_requete(
                request,
                action="CREATION_CIBLE",
                ressource=cible.valeur,
                details=f"Ajout de la cible '{cible.valeur}' ({cible.get_type_display()}) au projet '{project.nom}'.",
                projet=project
            )

            return json_response({
                'message': 'Cible ajoutée au projet avec succès.',
                'cible': {
                    'id': str(cible.id),
                    'valeur': cible.valeur,
                    'type': cible.type,
                    'environnement': cible.environnement,
                    'statut': cible.statut,
                    'accessibilite': {'accessible': accessible, 'message': acc_msg}
                }
            }, status=201)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def cible_verify_view(request, cible_id):
    """POST: Appelle verifierAccessibilite() et verifierAutorisation() sur la cible."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        cible = Cible.objects.get(id=cible_id)
        access_ok, access_msg = cible.verifierAccessibilite()
        auth_ok, auth_msg = cible.verifierAutorisation()

        JournalActivite.enregistrer_depuis_requete(
            request,
            action="VERIFICATION_CIBLE",
            ressource=cible.valeur,
            details=f"Vérification d'accessibilité ({access_ok}) et d'autorisation ({auth_ok}) sur '{cible.valeur}'.",
            projet=cible.projet
        )

        return json_response({
            'cible_id': str(cible.id),
            'valeur': cible.valeur,
            'statut_actuel': cible.statut,
            'accessibilite': {
                'valide': access_ok,
                'message': access_msg
            },
            'autorisation': {
                'valide': auth_ok,
                'message': auth_msg
            }
        })
    except Cible.DoesNotExist:
        return json_response({'error': 'Cible non trouvée.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def cible_authorizations_view(request, cible_id):
    """POST: Ajouter une AutorisationCible."""
    try:
        cible = Cible.objects.get(id=cible_id)
    except Cible.DoesNotExist:
        return json_response({'error': 'Cible non trouvée.'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_debut = data.get('dateDebut')
            date_fin = data.get('dateFin')
            preuve = data.get('preuve')
            tests_actifs = data.get('testsActifsAutorises', False)
            commentaire = data.get('commentaire', '')

            if not date_debut or not date_fin or not preuve:
                return json_response({'error': 'Les champs dateDebut, dateFin et preuve sont obligatoires.'}, status=400)

            if isinstance(date_debut, str):
                date_debut = datetime.date.fromisoformat(date_debut)
            if isinstance(date_fin, str):
                date_fin = datetime.date.fromisoformat(date_fin)

            auth = AutorisationCible.objects.create(
                cible=cible,
                dateDebut=date_debut,
                dateFin=date_fin,
                preuve=preuve,
                testsActifsAutorises=tests_actifs,
                commentaire=commentaire
            )

            JournalActivite.enregistrer_depuis_requete(
                request,
                action="AJOUT_AUTORISATION_SCAN",
                ressource=cible.valeur,
                details=f"Ajout d'une autorisation de scan pour la cible '{cible.valeur}' (Preuve: {preuve}).",
                projet=cible.projet
            )


            # Re-verify target authorization status
            cible.verifierAutorisation()

            return json_response({
                'message': 'Autorisation ajoutée avec succès.',
                'autorisation': {
                    'id': str(auth.id),
                    'dateDebut': str(auth.dateDebut),
                    'dateFin': str(auth.dateFin),
                    'preuve': auth.preuve,
                    'estValide': auth.estValide(),
                    'cible_statut': cible.statut
                }
            }, status=201)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)
