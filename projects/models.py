import uuid
import re
from django.db import models
from django.utils import timezone


class StatutProjet(models.TextChoices):
    BROUILLON = 'BROUILLON', 'Brouillon'
    ACTIF = 'ACTIF', 'Actif'
    SUSPENDU = 'SUSPENDU', 'Suspendu'
    ARCHIVE = 'ARCHIVE', 'Archivé'


class TypeCible(models.TextChoices):
    URL = 'URL', 'URL Web'
    DOMAINE = 'DOMAINE', 'Nom de domaine'
    ADRESSE_IP = 'ADRESSE_IP', 'Adresse IP'
    API_REST = 'API_REST', 'API REST'
    API_GRAPHQL = 'API_GRAPHQL', 'API GraphQL'


class Environnement(models.TextChoices):
    DEVELOPPEMENT = 'DEVELOPPEMENT', 'Développement'
    TEST = 'TEST', 'Test / QA'
    PREPRODUCTION = 'PREPRODUCTION', 'Pré-production'
    PRODUCTION = 'PRODUCTION', 'Production'
    LABORATOIRE = 'LABORATOIRE', 'Laboratoire de sécurité'


class StatutCible(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente d\'autorisation'
    AUTORISEE = 'AUTORISEE', 'Autorisée'
    REFUSEE = 'REFUSEE', 'Refusée'
    SUSPENDUE = 'SUSPENDUE', 'Suspendue'
    EXPIREE = 'EXPIREE', 'Expirée'


class Projet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=255, verbose_name="Nom du projet")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    organisation = models.CharField(max_length=255, verbose_name="Organisation")
    statut = models.CharField(
        max_length=20,
        choices=StatutProjet.choices,
        default=StatutProjet.ACTIF,
        verbose_name="Statut"
    )
    dateCreation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    dateArchivage = models.DateTimeField(null=True, blank=True, verbose_name="Date d'archivage")

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"
        ordering = ['-dateCreation']

    def __str__(self):
        return f"{self.nom} ({self.organisation})"

    @classmethod
    def creer(cls, nom, organisation, description="", statut=StatutProjet.ACTIF):
        """Méthode métier creer() définie dans PlantUML."""
        projet = cls(
            nom=nom,
            organisation=organisation,
            description=description,
            statut=statut
        )
        projet.save()
        return projet

    def modifier(self, nom=None, description=None, organisation=None, statut=None):
        """Méthode métier modifier() définie dans PlantUML."""
        fields_to_update = []
        if nom is not None and nom.strip() != "":
            self.nom = nom.strip()
            fields_to_update.append('nom')

        if description is not None:
            self.description = description
            fields_to_update.append('description')

        if organisation is not None and organisation.strip() != "":
            self.organisation = organisation.strip()
            fields_to_update.append('organisation')

        if statut is not None and statut in StatutProjet.values:
            self.statut = statut
            fields_to_update.append('statut')

        if fields_to_update:
            self.save(update_fields=fields_to_update)
        return self

    def archiver(self):
        """Méthode métier archiver() définie dans PlantUML."""
        self.statut = StatutProjet.ARCHIVE
        self.dateArchivage = timezone.now()
        self.save(update_fields=['statut', 'dateArchivage'])
        return self

    def supprimer(self):
        """Méthode métier supprimer() définie dans PlantUML."""
        self.delete()
        return True


class Cible(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name="cibles",
        verbose_name="Projet"
    )
    valeur = models.CharField(max_length=512, verbose_name="Valeur de la cible (URL, IP, Domaine)")
    type = models.CharField(
        max_length=20,
        choices=TypeCible.choices,
        default=TypeCible.URL,
        verbose_name="Type de cible"
    )
    environnement = models.CharField(
        max_length=20,
        choices=Environnement.choices,
        default=Environnement.TEST,
        verbose_name="Environnement"
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutCible.choices,
        default=StatutCible.EN_ATTENTE,
        verbose_name="Statut d'autorisation"
    )
    dateAjout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")

    class Meta:
        verbose_name = "Cible"
        verbose_name_plural = "Cibles"
        ordering = ['-dateAjout']

    def __str__(self):
        return f"Cible: {self.valeur} [{self.get_type_display()}]"

    def verifierAccessibilite(self):
        """
        Méthode métier verifierAccessibilite() définie dans PlantUML.
        Vérifie la validité du format de la valeur selon le type.
        """
        val = self.valeur.strip()
        if not val:
            return False, "La valeur de la cible est vide."

        if self.type in [TypeCible.URL, TypeCible.API_REST, TypeCible.API_GRAPHQL]:
            if re.match(r'^https?://', val, re.IGNORECASE):
                return True, "Cible accessible : format URL valide."
            return False, "Format URL invalide. L'URL doit commencer par http:// ou https://."
        elif self.type == TypeCible.DOMAINE:
            if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', val):
                return True, "Nom de domaine valide."
            return False, "Format de domaine invalide."
        elif self.type == TypeCible.ADRESSE_IP:
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', val):
                return True, "Adresse IP valide."
            return False, "Format d'adresse IP invalide."

        return True, "Format valide."

    def verifierAutorisation(self):
        """
        Méthode métier verifierAutorisation() définie dans PlantUML.
        Vérifie si la cible possède au moins une autorisation valide et met à jour son statut.
        """
        autorisations = self.autorisations.all()
        for auth in autorisations:
            if auth.estValide():
                if self.statut != StatutCible.AUTORISEE:
                    self.statut = StatutCible.AUTORISEE
                    self.save(update_fields=['statut'])
                return True, "Autorisation valide confirmée."

        if self.statut == StatutCible.AUTORISEE:
            self.statut = StatutCible.EXPIREE
            self.save(update_fields=['statut'])

        return False, "Aucune autorisation valide trouvée pour cette cible."


class AutorisationCible(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cible = models.ForeignKey(
        Cible,
        on_delete=models.CASCADE,
        related_name="autorisations",
        verbose_name="Cible"
    )
    dateDebut = models.DateField(verbose_name="Date de début")
    dateFin = models.DateField(verbose_name="Date de fin")
    preuve = models.CharField(max_length=512, verbose_name="Preuve d'autorisation (Document / Ref)")
    testsActifsAutorises = models.BooleanField(default=False, verbose_name="Tests actifs autorisés (Scans destructifs)")
    commentaire = models.TextField(blank=True, default="", verbose_name="Commentaires & Scope")

    class Meta:
        verbose_name = "Autorisation de Cible"
        verbose_name_plural = "Autorisations de Cibles"
        ordering = ['-dateDebut']

    def __str__(self):
        return f"Autorisation pour {self.cible.valeur} ({self.dateDebut} au {self.dateFin})"

    def estValide(self):
        """
        Méthode métier estValide() : Boolean définie dans PlantUML.
        Vérifie si la date actuelle est comprise entre dateDebut et dateFin.
        """
        today = timezone.now().date()
        return self.dateDebut <= today <= self.dateFin
