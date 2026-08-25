import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


class StatutUtilisateur(models.TextChoices):
    INVITE = 'INVITE', 'Invité'
    ACTIF = 'ACTIF', 'Actif'
    SUSPENDU = 'SUSPENDU', 'Suspendu'
    BLOQUE = 'BLOQUE', 'Bloqué'
    DESACTIVE = 'DESACTIVE', 'Désactivé'


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, verbose_name="Code")
    description = models.TextField(blank=True, default="", verbose_name="Description")

    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ['code']

    def __str__(self):
        return self.code


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
        verbose_name="Permissions"
    )

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, nom, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        if not nom:
            raise ValueError("Le nom est obligatoire.")

        email = self.normalize_email(email)
        user = self.model(email=email, nom=nom, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nom, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('statut', StatutUtilisateur.ACTIF)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser doit avoir is_superuser=True.')

        return self.create_user(email, nom, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=255, verbose_name="Nom")
    email = models.EmailField(unique=True, verbose_name="Email")
    statut = models.CharField(
        max_length=20,
        choices=StatutUtilisateur.choices,
        default=StatutUtilisateur.ACTIF,
        verbose_name="Statut"
    )
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    derniereConnexion = models.DateTimeField(null=True, blank=True, verbose_name="Dernière connexion")

    roles = models.ManyToManyField(
        Role,
        related_name="utilisateurs",
        blank=True,
        verbose_name="Rôles"
    )

    is_staff = models.BooleanField(default=False, verbose_name="Accès administration")
    is_superuser = models.BooleanField(default=False, verbose_name="Super-utilisateur")

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"{self.nom} ({self.email})"

    @property
    def motDePasseHash(self):
        """Getter pour motDePasseHash (correspond au hash de password dans Django)."""
        return self.password

    @motDePasseHash.setter
    def motDePasseHash(self, raw_password):
        """Setter pour hasher et définir le mot de passe."""
        self.set_password(raw_password)

    @property
    def is_active(self):
        """Compatibilité authentification Django : actif si statut est ACTIF."""
        return self.statut == StatutUtilisateur.ACTIF

    @is_active.setter
    def is_active(self, value):
        if value:
            self.statut = StatutUtilisateur.ACTIF
        else:
            if self.statut == StatutUtilisateur.ACTIF:
                self.statut = StatutUtilisateur.DESACTIVE

    def seConnecter(self, mot_de_passe):
        """
        Authentifie l'utilisateur avec son mot de passe.
        Met à jour la date de dernière connexion si l'authentification réussit et que le statut est ACTIF.
        """
        if self.statut != StatutUtilisateur.ACTIF:
            return False, f"Impossible de se connecter : statut utilisateur '{self.get_statut_display()}'."

        if self.check_password(mot_de_passe):
            self.derniereConnexion = timezone.now()
            self.save(update_fields=['derniereConnexion'])
            return True, "Connexion réussie."

        return False, "Mot de passe incorrect."

    def seDeconnecter(self):
        """
        Gère la déconnexion de l'utilisateur.
        """
        return True, "Déconnexion réussie."

    def modifierProfil(self, nom=None, email=None, password=None):
        """
        Permet de modifier le profil utilisateur (nom, email, mot de passe).
        """
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
