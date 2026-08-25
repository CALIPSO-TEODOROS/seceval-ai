from django.core.management.base import BaseCommand
from users.models import Utilisateur, Role, Permission, StatutUtilisateur, MembreProjet


class Command(BaseCommand):
    help = "Peuple la base de données avec des utilisateurs, rôles, permissions et membres de projet initiaux."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Lancement du Seeder de securite ==="))

        # 1. Permissions
        permissions_data = [
            ("PERM_USER_MANAGE", "Gérer les utilisateurs, statuts et rôles"),
            ("PERM_SCAN_CREATE", "Créer et exécuter des évaluations de sécurité IA"),
            ("PERM_SCAN_READ", "Consulter les rapports et vulnérabilités détectées"),
            ("PERM_PROJECT_READ", "Accéder aux projets et cibles d'évaluation"),
        ]

        perms_objs = {}
        for code, desc in permissions_data:
            perm, created = Permission.objects.get_or_create(code=code, defaults={'description': desc})
            perms_objs[code] = perm
            status_str = "Créée" if created else "Existante"
            self.stdout.write(f"  [Permission] {code} ({status_str})")

        # 2. Roles
        roles_config = [
            ("Administrateur", "Accès total au système d'évaluation et de gestion", list(perms_objs.values())),
            ("Auditeur Sécurité", "Capacité à créer et consulter les évaluations de sécurité", [perms_objs["PERM_SCAN_CREATE"], perms_objs["PERM_SCAN_READ"], perms_objs["PERM_PROJECT_READ"]]),
            ("Lecteur", "Consultation des rapports de sécurité", [perms_objs["PERM_SCAN_READ"], perms_objs["PERM_PROJECT_READ"]]),
        ]

        roles_objs = {}
        for nom, desc, perms_list in roles_config:
            role, created = Role.objects.get_or_create(nom=nom, defaults={'description': desc})
            role.permissions.set(perms_list)
            roles_objs[nom] = role
            status_str = "Créé" if created else "Existant"
            self.stdout.write(f"  [Rôle] {nom} ({status_str})")

        # 3. Utilisateurs par défaut
        users_data = [
            {
                "email": "admin@seceval.io",
                "nom": "Administrateur Système",
                "password": "AdminPassword123!",
                "statut": StatutUtilisateur.ACTIF,
                "role": roles_objs["Administrateur"],
                "is_staff": True,
                "is_superuser": True
            },
            {
                "email": "auditeur@seceval.io",
                "nom": "Jean Auditeur",
                "password": "AuditeurPass123!",
                "statut": StatutUtilisateur.ACTIF,
                "role": roles_objs["Auditeur Sécurité"],
                "is_staff": False,
                "is_superuser": False
            },
            {
                "email": "lecteur@seceval.io",
                "nom": "Marie Lectrice",
                "password": "LecteurPass123!",
                "statut": StatutUtilisateur.ACTIF,
                "role": roles_objs["Lecteur"],
                "is_staff": False,
                "is_superuser": False
            }
        ]

        created_users = []
        for udata in users_data:
            user = Utilisateur.objects.filter(email=udata["email"]).first()
            if not user:
                user = Utilisateur.objects.create_user(
                    email=udata["email"],
                    nom=udata["nom"],
                    password=udata["password"],
                    statut=udata["statut"],
                    is_staff=udata["is_staff"],
                    is_superuser=udata["is_superuser"]
                )
                user.roles.add(udata["role"])
                self.stdout.write(self.style.SUCCESS(f"  [Utilisateur] Créé : {user.email} (Mot de passe: {udata['password']})"))
            else:
                user.roles.add(udata["role"])
                self.stdout.write(f"  [Utilisateur] Existant : {user.email}")
            created_users.append(user)

        # 4. Membres de projet
        for user in created_users:
            if not MembreProjet.objects.filter(utilisateur=user).exists():
                membre = MembreProjet.objects.create(utilisateur=user, actif=True)
                self.stdout.write(f"  [MembreProjet] Affecté : {user.nom}")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seeder termine avec succes !"))
