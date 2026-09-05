import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from .models import Utilisateur, Role, Permission, StatutUtilisateur, MembreProjet
from logs_app.models import JournalActivite


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False, 'indent': 2})


def login_page_view(request):
    """Rend la page de connexion dédiée (sans option d'inscription)."""
    if request.user.is_authenticated:
        return redirect('/web/')
    try:
        return render(request, 'users/login.html')
    except Exception:
        return render(request, 'login.html')



def web_ui_view(request):
    """Rend la page HTML du tableau de bord sous /web/. Redirige vers /web/login/ si non authentifié."""
    if not request.user.is_authenticated:
        return redirect('/web/login/')
    try:
        return render(request, 'users/index.html')
    except Exception:
        return render(request, 'index.html')




@csrf_exempt
def register_view(request):
    """Endpoint pour l'inscription d'un nouvel utilisateur."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        nom = data.get('nom')
        password = data.get('password')
        statut = data.get('statut', StatutUtilisateur.ACTIF)

        if not email or not nom or not password:
            return json_response({'error': 'Les champs email, nom et password sont requis.'}, status=400)

        if Utilisateur.objects.filter(email=email).exists():
            return json_response({'error': 'Un utilisateur avec cet email existe déjà.'}, status=400)

        user = Utilisateur.objects.create_user(
            email=email,
            nom=nom,
            password=password,
            statut=statut
        )

        JournalActivite.enregistrer_depuis_requete(
            request,
            action="CREATION_UTILISATEUR",
            ressource=user.email,
            details=f"Création de l'utilisateur '{user.nom}' ({user.email})."
        )

        return json_response({
            'message': 'Utilisateur créé avec succès.',
            'user': {
                'id': str(user.id),
                'nom': user.nom,
                'email': user.email,
                'statut': user.statut,
                'dateCreation': user.dateCreation.isoformat()
            }
        }, status=201)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def login_view(request):
    """Endpoint pour la connexion d'un utilisateur (appel de seConnecter)."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return json_response({'error': 'L\'email et le mot de passe sont requis.'}, status=400)

        try:
            user = Utilisateur.objects.get(email=email)
        except Utilisateur.DoesNotExist:
            return json_response({'error': 'Identifiants invalides.'}, status=401)

        success, message = user.seConnecter(password)
        if success:
            login(request, user)
            JournalActivite.enregistrer_depuis_requete(
                request,
                action="CONNEXION_UTILISATEUR",
                ressource=user.email,
                details=f"Connexion réussie de '{user.nom}'."
            )
            return json_response({
                'message': message,
                'user': {
                    'id': str(user.id),
                    'nom': user.nom,
                    'email': user.email,
                    'statut': user.statut,
                    'derniereConnexion': user.derniereConnexion.isoformat() if user.derniereConnexion else None
                }
            }, status=200)
        else:
            return json_response({'error': message}, status=401)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def logout_view(request):
    """Endpoint pour la déconnexion d'un utilisateur (appel de seDeconnecter)."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    if request.user.is_authenticated:
        user_email = request.user.email
        if hasattr(request.user, 'seDeconnecter'):
            request.user.seDeconnecter()
        logout(request)
        JournalActivite.enregistrer(
            utilisateur=None,
            action="DECONNEXION_UTILISATEUR",
            ressource=user_email,
            details=f"Déconnexion de l'utilisateur '{user_email}'.",
            adresseIP=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return json_response({'message': 'Déconnexion réussie.'}, status=200)
    else:
        logout(request)
        return json_response({'message': 'Déconnexion réussie (session fermée).'}, status=200)


@csrf_exempt
def profile_view(request):
    """Endpoint pour la consultation et modification du profil utilisateur."""
    if not request.user.is_authenticated:
        return json_response({'error': 'Authentification requise.'}, status=401)

    user = request.user

    if request.method == 'GET':
        return json_response({
            'id': str(user.id),
            'nom': user.nom,
            'email': user.email,
            'statut': user.statut,
            'dateCreation': user.dateCreation.isoformat(),
            'derniereConnexion': user.derniereConnexion.isoformat() if user.derniereConnexion else None,
            'roles': [{'id': str(role.id), 'nom': role.nom} for role in user.roles.all()]
        })

    elif request.method in ['PUT', 'PATCH']:
        try:
            data = json.loads(request.body)
            user.modifierProfil(
                nom=data.get('nom'),
                email=data.get('email'),
                password=data.get('password')
            )
            return json_response({
                'message': 'Profil mis à jour avec succès.',
                'user': {
                    'id': str(user.id),
                    'nom': user.nom,
                    'email': user.email,
                    'statut': user.statut
                }
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def users_list_view(request):
    """Liste de tous les utilisateurs pour le dashboard."""
    if request.method != 'GET':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    users = Utilisateur.objects.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': str(user.id),
            'nom': user.nom,
            'email': user.email,
            'statut': user.statut,
            'statut_display': user.get_statut_display(),
            'dateCreation': user.dateCreation.isoformat(),
            'derniereConnexion': user.derniereConnexion.isoformat() if user.derniereConnexion else None,
            'roles': [r.nom for r in user.roles.all()],
            'is_staff': user.is_staff
        })

    return json_response({
        'total': len(user_list),
        'users': user_list
    })


@csrf_exempt
def user_status_change_view(request, user_id):
    """Modifie le statut d'un utilisateur."""
    if request.method != 'POST':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    try:
        data = json.loads(request.body)
        new_statut = data.get('statut')

        if new_statut not in StatutUtilisateur.values:
            return json_response({'error': f'Statut invalide. Valeurs permises: {StatutUtilisateur.values}'}, status=400)

        user = Utilisateur.objects.get(id=user_id)
        user.statut = new_statut
        user.save(update_fields=['statut'])

        return json_response({
            'message': f'Statut de {user.nom} mis à jour avec succès.',
            'user': {
                'id': str(user.id),
                'nom': user.nom,
                'statut': user.statut,
                'statut_display': user.get_statut_display()
            }
        })
    except Utilisateur.DoesNotExist:
        return json_response({'error': 'Utilisateur non trouvé.'}, status=404)
    except Exception as e:
        return json_response({'error': str(e)}, status=400)


@csrf_exempt
def roles_list_view(request):
    """GET: Liste des rôles et permissions. POST: Créer un nouveau rôle."""
    if request.method == 'GET':
        roles = Role.objects.all()
        permissions = Permission.objects.all()

        roles_data = []
        for r in roles:
            roles_data.append({
                'id': str(r.id),
                'nom': r.nom,
                'description': r.description,
                'permissions': [p.code for p in r.permissions.all()]
            })

        perms_data = [{'id': str(p.id), 'code': p.code, 'description': p.description} for p in permissions]

        return json_response({
            'roles': roles_data,
            'permissions': perms_data
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            nom = data.get('nom')
            description = data.get('description', '')
            perm_codes = data.get('permissions', [])

            if not nom:
                return json_response({'error': 'Le nom du rôle est requis.'}, status=400)

            role, created = Role.objects.get_or_create(nom=nom, defaults={'description': description})
            if not created:
                role.description = description
                role.save()

            if perm_codes:
                perms = Permission.objects.filter(code__in=perm_codes)
                role.permissions.set(perms)

            return json_response({
                'message': 'Rôle créé ou mis à jour avec succès.',
                'role': {
                    'id': str(role.id),
                    'nom': role.nom,
                    'description': role.description,
                    'permissions': [p.code for p in role.permissions.all()]
                }
            }, status=201)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def members_list_view(request):
    """GET: Liste des membres de projet. POST: Affecter un utilisateur comme membre."""
    if request.method == 'GET':
        members = MembreProjet.objects.select_related('utilisateur').all()
        members_data = []
        for m in members:
            members_data.append({
                'id': str(m.id),
                'utilisateur_id': str(m.utilisateur.id),
                'nom': m.utilisateur.nom,
                'email': m.utilisateur.email,
                'dateAffectation': m.dateAffectation.isoformat(),
                'actif': m.actif
            })
        return json_response({'members': members_data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            utilisateur_id = data.get('utilisateur_id')
            actif = data.get('actif', True)

            if not utilisateur_id:
                return json_response({'error': 'L\'id de l\'utilisateur est requis.'}, status=400)

            user = Utilisateur.objects.get(id=utilisateur_id)
            member = MembreProjet.objects.create(utilisateur=user, actif=actif)

            return json_response({
                'message': 'Membre de projet affecté avec succès.',
                'member': {
                    'id': str(member.id),
                    'nom': user.nom,
                    'email': user.email,
                    'dateAffectation': member.dateAffectation.isoformat(),
                    'actif': member.actif
                }
            }, status=201)
        except Utilisateur.DoesNotExist:
            return json_response({'error': 'Utilisateur introuvable.'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
def dashboard_stats_view(request):
    """GET: Endpoints agrégé retournant toutes les métriques exécutives pour le Tableau de Bord."""
    if request.method != 'GET':
        return json_response({'error': 'Méthode non autorisée.'}, status=405)

    from projects.models import Projet
    from audits.models import Audit, StatutAudit
    from vulns.models import Vulnerabilite, Gravite
    from reports.models import Rapport
    from notifications_app.models import Notification
    from logs_app.models import JournalActivite
    from django.db.models import Avg

    # KPIs
    score_avg = Audit.objects.aggregate(Avg('scoreSecurite'))['scoreSecurite__avg'] or 100.0

    vulns_qs = Vulnerabilite.objects.all()
    vulns_total = vulns_qs.count()
    vulns_critique = vulns_qs.filter(gravite=Gravite.CRITIQUE).count()
    vulns_elevee = vulns_qs.filter(gravite=Gravite.ELEVEE).count()
    vulns_moyenne = vulns_qs.filter(gravite=Gravite.MOYENNE).count()
    vulns_faible = vulns_qs.filter(gravite=Gravite.FAIBLE).count()
    vulns_info = vulns_qs.filter(gravite=Gravite.INFORMATION).count()

    audits_qs = Audit.objects.select_related('cible', 'projet').all()
    audits_total = audits_qs.count()
    audits_running = audits_qs.filter(statut=StatutAudit.EN_COURS).count()
    audits_completed = audits_qs.filter(statut=StatutAudit.TERMINE).count()

    projects_qs = Projet.objects.all()
    projects_total = projects_qs.count()
    projects_active = projects_qs.filter(statut='ACTIF').count()

    notifs_total = Notification.objects.count()
    notifs_sent = Notification.objects.filter(statut='ENVOYE').count()

    reports_total = Rapport.objects.count()
    reports_published = Rapport.objects.filter(statut='PUBLIE').count()

    logs_total = JournalActivite.objects.count()

    # Lists for feed displays
    recent_audits = [
        {
            'id': str(a.id),
            'type_display': a.get_type_display(),
            'cible': a.cible.valeur,
            'projet': a.projet.nom,
            'statut': a.statut,
            'statut_display': a.get_statut_display(),
            'progression': a.progression,
            'scoreSecurite': round(a.scoreSecurite, 1)
        }
        for a in audits_qs[:5]
    ]

    recent_vulns = [
        {
            'id': str(v.id),
            'titre': v.titre,
            'gravite': v.gravite,
            'scoreCVSS': v.scoreCVSS,
            'codeCWE': v.codeCWE,
            'statut': v.statut,
            'statut_display': v.get_statut_display(),
            'cible': v.audit.cible.valeur
        }
        for v in vulns_qs.select_related('audit', 'audit__cible')[:5]
    ]

    recent_notifs = [
        {
            'id': str(n.id),
            'canal': n.canal,
            'sujet': n.sujet,
            'statut': n.statut,
            'destinataire': n.destinataire.nom,
            'dateEnvoi': n.dateEnvoi.isoformat() if n.dateEnvoi else None
        }
        for n in Notification.objects.select_related('destinataire')[:5]
    ]

    recent_logs = [
        {
            'id': str(l.id),
            'action': l.action,
            'ressource': l.ressource,
            'utilisateur': l.utilisateur.nom,
            'adresseIP': l.adresseIP,
            'dateAction': l.dateAction.isoformat()
        }
        for l in JournalActivite.objects.select_related('utilisateur')[:5]
    ]

    # Scores trend curve
    trend_scores = [round(a.scoreSecurite, 1) for a in audits_qs.order_by('dateCreation')[:10]]

    return json_response({
        'kpis': {
            'score_moyen': round(score_avg, 1),
            'vulns_total': vulns_total,
            'vulns_critique': vulns_critique,
            'vulns_elevee': vulns_elevee,
            'vulns_moyenne': vulns_moyenne,
            'vulns_faible': vulns_faible,
            'vulns_info': vulns_info,
            'audits_total': audits_total,
            'audits_running': audits_running,
            'audits_completed': audits_completed,
            'projects_total': projects_total,
            'projects_active': projects_active,
            'notifs_total': notifs_total,
            'notifs_sent': notifs_sent,
            'reports_total': reports_total,
            'reports_published': reports_published,
            'logs_total': logs_total
        },
        'recent_audits': recent_audits,
        'recent_vulns': recent_vulns,
        'recent_notifs': recent_notifs,
        'recent_logs': recent_logs,
        'trend_scores': trend_scores
    })

