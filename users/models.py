# ==============================================================================
# SEC-EVAL AI - MODULE USERS (MODÈLES DE DONNÉES UTILISATEURS & PERMISSIONS)
# ==============================================================================
# Ce fichier définit la structure de données pour les utilisateurs, les rôles,
# les permissions système et l'affectation des membres aux projets de sécurité.
# ==============================================================================

import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


class StatutUtilisateur(models.TextChoices):
    """
    Énumération des statuts possibles pour un compte utilisateur dans la plateforme.
    - INVITE : Compte nouvellement créé en attente de validation.
    - ACTIF : Compte pleinement opérationnel et autorisé à se connecter.
    - SUSPENDU : Compte temporairement restreint.
    - BLOQUE : Compte verrouillé suite à des échecs de sécurité.
    - DESACTIVE : Compte désactivé par l'administrateur.
    """
    INVITE = 'INVITE', 'Invité'
    ACTIF = 'ACTIF', 'Actif'
    SUSPENDU = 'SUSPENDU', 'Suspendu'
    BLOQUE = 'BLOQUE', 'Bloqué'
    DESACTIVE = 'DESACTIVE', 'Désactivé'


class Permission(models.Model):
    """
    Modèle représentant une permission système atomique (ex: PERM_USER_MANAGE, PERM_SCAN_CREATE).
    Chaque permission identifie une capacité d'action spécifique sur la plateforme.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Identifiant unique UUIDv4
    code = models.CharField(max_length=100, unique=True, verbose_name="Code")   # Code unique de la permission
    description = models.TextField(blank=True, default="", verbose_name="Description") # Explication du rôle de la permission

    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ['code']

    def __str__(self):
        return self.code


class Role(models.Model):
    """
    Modèle représentant un Rôle Système (ex: Administrateur, Auditeur Sécurité, Lecteur).
    Un rôle regroupe un ensemble de permissions système réutilisables.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # Identifiant unique UUIDv4
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom")       # Intitulé du rôle
    description = models.TextField(blank=True, default="", verbose_name="Description") # Description du périmètre d'action du rôle
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
        verbose_name="Permissions"
    ) # Association Many-to-Many avec les permissions système

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class UtilisateurManager(BaseUserManager):
    """
    Gestionnaire personnalisée des comptes Utilisateur (remplace le UserManager natif de Django).
    """
    def create_user(self, email, nom, password=None, **extra_fields):
        """Crée et enregistre un utilisateur standard avec adresse email normalisée."""
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        if not nom:
            raise ValueError("Le nom est obligatoire.")

        email = self.normalize_email(email)
        user = self.model(email=email, nom=nom, **extra_fields)
        if password:
            user.set_password(password) # Hashage sécurisé du mot de passe avec PBKDF2
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nom, password=None, **extra_fields):
        """Crée et enregistre un super-utilisateur (administrateur principal)."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('statut', StatutUtilisateur.ACTIF)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser doit avoir is_superuser=True.')

        return self.create_user(email, nom, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    Modèle d'Utilisateur Personnalisé héritant de AbstractBaseUser.
    Utilise l'adresse email comme identifiant de connexion principal (USERNAME_FIELD).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # Identifiant unique UUIDv4
    nom = models.CharField(max_length=255, verbose_name="Nom")                  # Nom complet ou pseudo de l'utilisateur
    email = models.EmailField(unique=True, verbose_name="Email")                # Adresse email unique de connexion
    statut = models.CharField(
        max_length=20,
        choices=StatutUtilisateur.choices,
        default=StatutUtilisateur.ACTIF,
        verbose_name="Statut"
    ) # Statut du compte (ACTIF par défaut)
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création") # Horodatage de création
    derniereConnexion = models.DateTimeField(null=True, blank=True, verbose_name="Dernière connexion") # Horodatage de dernière connexion

    roles = models.ManyToManyField(
        Role,
        related_name="utilisateurs",
        blank=True,
        verbose_name="Rôles"
    ) # Rôles attribués à l'utilisateur

    is_staff = models.BooleanField(default=False, verbose_name="Accès administration")
    is_superuser = models.BooleanField(default=False, verbose_name="Super-utilisateur")

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'     # Identifiant de connexion principal
    REQUIRED_FIELDS = ['nom']    # Champs requis lors de la création d'un superuser

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"{self.nom} ({self.email})"

    @property
    def motDePasseHash(self):
        """Propriété retournant le hash PBKDF2 du mot de passe."""
        return self.password

    @motDePasseHash.setter
    def motDePasseHash(self, raw_password):
        """Définit et hashe le mot de passe brut."""
        self.set_password(raw_password)

    @property
    def is_active(self):
        """Retourne True si le compte est au statut ACTIF pour l'authentification Django."""
        return self.statut == StatutUtilisateur.ACTIF

    @is_active.setter
    def is_active(self, value):
        """Met à jour le statut en fonction du booléen is_active."""
        if value:
            self.statut = StatutUtilisateur.ACTIF
        else:
            if self.statut == StatutUtilisateur.ACTIF:
                self.statut = StatutUtilisateur.DESACTIVE

    def seConnecter(self, mot_de_passe):
        """Méthode métier pour valider le mot de passe et mettre à jour la date de dernière connexion."""
        if self.statut != StatutUtilisateur.ACTIF:
            return False, f"Impossible de se connecter : statut utilisateur '{self.get_statut_display()}'."

        if self.check_password(mot_de_passe):
            self.derniereConnexion = timezone.now()
            self.save(update_fields=['derniereConnexion'])
            return True, "Connexion réussie."

        return False, "Mot de passe incorrect."

    def seDeconnecter(self):
        """Méthode métier pour enregistrer la déconnexion."""
        return True, "Déconnexion réussie."

    def modifierProfil(self, nom=None, email=None, password=None):
        """Permet de mettre à jour dynamiquement les informations du profil utilisateur."""
        fields_to_update = []
        if nom is not None and nom.strip() != "":
            self.nom = nom.strip()
            fields_to_update.append('nom')

        if email is not None and email.strip() != "":
            self.email = self.__class__.objects.normalize_email(email.strip())
            fields_to_update.append('email')

        if password is not None and password != "":
            self.set_password(password)
            fields_to_update.append('password')

        if fields_to_update:
            self.save(update_fields=fields_to_update)

        return self


class MembreProjet(models.Model):
    """
    Modèle d'affectation d'un utilisateur à un projet de sécurité spécifique.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="membres_projet",
        verbose_name="Utilisateur"
    )
    projet = models.ForeignKey(
        'projects.Projet',
        on_delete=models.CASCADE,
        related_name="membres",
        null=True,
        blank=True,
        verbose_name="Projet"
    )
    dateAffectation = models.DateTimeField(auto_now_add=True, verbose_name="Date d'affectation")
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Membre de Projet"
        verbose_name_plural = "Membres de Projet"
        ordering = ['-dateAffectation']

    def __str__(self):
        return f"MembreProjet: {self.utilisateur.nom} (Actif: {self.actif})"
