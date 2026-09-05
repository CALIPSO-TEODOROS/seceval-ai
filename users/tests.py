import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from users.models import (
    Utilisateur,
    Role,
    Permission,
    StatutUtilisateur,
    MembreProjet
)


class UserManagementModelTests(TestCase):

    def setUp(self):
        self.perm_scan = Permission.objects.create(
            code="PERM_SCAN_EXECUTE",
            description="Exécuter un scan de sécurité"
        )
        self.role_auditeur = Role.objects.create(
            nom="Auditeur",
            description="Rôle pour les auditeurs de sécurité"
        )
        self.role_auditeur.permissions.add(self.perm_scan)

    def test_permission_creation(self):
        self.assertIsInstance(self.perm_scan.id, uuid.UUID)
        self.assertEqual(str(self.perm_scan), "PERM_SCAN_EXECUTE")

    def test_role_creation_and_permissions(self):
        self.assertIsInstance(self.role_auditeur.id, uuid.UUID)
        self.assertEqual(str(self.role_auditeur), "Auditeur")
        self.assertIn(self.perm_scan, self.role_auditeur.permissions.all())

    def test_utilisateur_creation_and_manager(self):
        user = Utilisateur.objects.create_user(
            email="test@secframe.io",
            nom="Jean Dupont",
            password="SecurePassword123!"
        )
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "test@secframe.io")
        self.assertEqual(user.nom, "Jean Dupont")
        self.assertEqual(user.statut, StatutUtilisateur.ACTIF)
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_mot_de_passe_hash_property(self):
        user = Utilisateur.objects.create_user(
            email="hash@secframe.io",
            nom="Hash Test",
            password="OldPassword"
        )
        self.assertTrue(user.motDePasseHash.startswith("pbkdf2_") or "$" in user.motDePasseHash)
        user.motDePasseHash = "NewPassword123"
        self.assertTrue(user.check_password("NewPassword123"))

    def test_superuser_creation(self):
        admin_user = Utilisateur.objects.create_superuser(
            email="admin@secframe.io",
            nom="Admin Sys",
            password="AdminPassWord123!"
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.statut, StatutUtilisateur.ACTIF)

    def test_se_connecter_success(self):
        user = Utilisateur.objects.create_user(
            email="login@secframe.io",
            nom="Login User",
            password="PassWord123!"
        )
        self.assertIsNone(user.derniereConnexion)
        success, message = user.seConnecter("PassWord123!")
        self.assertTrue(success)
        self.assertEqual(message, "Connexion réussie.")
        self.assertIsNotNone(user.derniereConnexion)

    def test_se_connecter_wrong_password(self):
        user = Utilisateur.objects.create_user(
            email="login_wrong@secframe.io",
            nom="Login Wrong User",
            password="PassWord123!"
        )
        success, message = user.seConnecter("WrongPass!")
        self.assertFalse(success)
        self.assertEqual(message, "Mot de passe incorrect.")

    def test_se_connecter_inactive_status(self):
        user = Utilisateur.objects.create_user(
            email="blocked@secframe.io",
            nom="Blocked User",
            password="PassWord123!",
            statut=StatutUtilisateur.BLOQUE
        )
        success, message = user.seConnecter("PassWord123!")
        self.assertFalse(success)
        self.assertIn("statut utilisateur", message)

    def test_se_deconnecter(self):
        user = Utilisateur.objects.create_user(
            email="logout@secframe.io",
            nom="Logout User",
            password="PassWord123!"
        )
        success, message = user.seDeconnecter()
        self.assertTrue(success)
        self.assertEqual(message, "Déconnexion réussie.")

    def test_modifier_profil(self):
        user = Utilisateur.objects.create_user(
            email="original@secframe.io",
            nom="Nom Original",
            password="Password1"
        )
        user.modifierProfil(nom="Nom Modifié", email="nouveau@secframe.io", password="NewPassword2")
        user.refresh_from_db()
        self.assertEqual(user.nom, "Nom Modifié")
        self.assertEqual(user.email, "nouveau@secframe.io")
        self.assertTrue(user.check_password("NewPassword2"))

    def test_membre_projet_creation(self):
        user = Utilisateur.objects.create_user(
            email="membre@secframe.io",
            nom="Membre Test",
            password="Password1"
        )
        membre = MembreProjet.objects.create(
            utilisateur=user,
            actif=True
        )
        self.assertIsInstance(membre.id, uuid.UUID)
        self.assertEqual(membre.utilisateur, user)
        self.assertTrue(membre.actif)
        self.assertIn("MembreProjet: Membre Test", str(membre))


class UserManagementAPITests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_login_page_view(self):
        response = self.client.get(reverse('users:login-page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SecEval AI - Connexion")

    def test_unauthenticated_web_redirect(self):
        response = self.client.get(reverse('users:web-ui'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/web/login/', response.url)

    def test_authenticated_web_access(self):
        user = Utilisateur.objects.create_user(
            email='auth_web@secframe.io',
            nom='Auth Web User',
            password='MyPassword123!'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('users:web-ui'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SecEval AI")


    def test_register_api(self):
        response = self.client.post(
            reverse('users:register'),
            data=json.dumps({
                'email': 'api_user@secframe.io',
                'nom': 'API User',
                'password': 'StrongPassword123!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['user']['email'], 'api_user@secframe.io')
        self.assertTrue(Utilisateur.objects.filter(email='api_user@secframe.io').exists())

    def test_login_api(self):
        user = Utilisateur.objects.create_user(
            email='login_api@secframe.io',
            nom='Login API User',
            password='MyPassword123!'
        )
        response = self.client.post(
            reverse('users:login'),
            data=json.dumps({
                'email': 'login_api@secframe.io',
                'password': 'MyPassword123!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['message'], 'Connexion réussie.')

    def test_profile_api(self):
        user = Utilisateur.objects.create_user(
            email='profile_api@secframe.io',
            nom='Profile User',
            password='MyPassword123!'
        )
        self.client.force_login(user)

        # GET Profile
        get_response = self.client.get(reverse('users:profile'))
        self.assertEqual(get_response.status_code, 200)
        get_data = get_response.json()
        self.assertEqual(get_data['email'], 'profile_api@secframe.io')

        # PUT/PATCH Profile
        patch_response = self.client.patch(
            reverse('users:profile'),
            data=json.dumps({
                'nom': 'Profile User Updated'
            }),
            content_type='application/json'
        )
        self.assertEqual(patch_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.nom, 'Profile User Updated')

    def test_users_list_and_status_change_api(self):
        user = Utilisateur.objects.create_user(
            email='user_list@secframe.io',
            nom='List User',
            password='Password123!'
        )
        role = Role.objects.create(nom="Auditeur Test", description="Desc")

        # List API
        list_response = self.client.get(reverse('users:users-list'))
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertGreaterEqual(list_data['total'], 1)

        # Status change API
        status_response = self.client.post(
            reverse('users:user-status-change', kwargs={'user_id': user.id}),
            data=json.dumps({'statut': StatutUtilisateur.SUSPENDU}),
            content_type='application/json'
        )
        self.assertEqual(status_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.SUSPENDU)

        # Role change API
        role_response = self.client.post(
            reverse('users:user-role-change', kwargs={'user_id': user.id}),
            data=json.dumps({'role_id': str(role.id)}),
            content_type='application/json'
        )
        self.assertEqual(role_response.status_code, 200)
        user.refresh_from_db()
        self.assertIn(role, user.roles.all())

    def test_roles_and_members_api(self):
        user = Utilisateur.objects.create_user(
            email='member_api@secframe.io',
            nom='Member API User',
            password='Password123!'
        )

        # Create Role
        role_response = self.client.post(
            reverse('users:roles-list'),
            data=json.dumps({'nom': 'Analyste', 'description': 'Analyste de failles'}),
            content_type='application/json'
        )
        self.assertEqual(role_response.status_code, 201)

        # Assign Member
        member_response = self.client.post(
            reverse('users:members-list'),
            data=json.dumps({'utilisateur_id': str(user.id), 'actif': True}),
            content_type='application/json'
        )
        self.assertEqual(member_response.status_code, 201)

    def test_seed_users_command(self):
        call_command('seed_users')
        self.assertTrue(Utilisateur.objects.filter(email='admin@seceval.io').exists())
        self.assertTrue(Utilisateur.objects.filter(email='auditeur@seceval.io').exists())
        self.assertTrue(Utilisateur.objects.filter(email='lecteur@seceval.io').exists())
        self.assertTrue(Role.objects.filter(nom='Administrateur').exists())
        self.assertTrue(Permission.objects.filter(code='PERM_USER_MANAGE').exists())
