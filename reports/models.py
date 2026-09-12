import uuid
import os
import json
from django.db import models
from django.utils import timezone
from django.conf import settings
from audits.models import Audit
from vulns.models import Vulnerabilite


class FormatRapport(models.TextChoices):
    PDF = 'PDF', 'Document PDF (.pdf)'
    HTML = 'HTML', 'Page Web HTML (.html)'
    JSON = 'JSON', 'Fichier structuré JSON (.json)'
    CSV = 'CSV', 'Fichier tabulaire CSV (.csv)'


class StatutRapport(models.TextChoices):
    BROUILLON = 'BROUILLON', 'Brouillon'
    EN_REVISION = 'EN_REVISION', 'En révision'
    VALIDE = 'VALIDE', 'Validé'
    REJETE = 'REJETE', 'Rejeté'
    PUBLIE = 'PUBLIE', 'Publié'


class Rapport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="rapports",
        verbose_name="Audit d'origine"
    )
    vulnerabilites = models.ManyToManyField(
        Vulnerabilite,
        blank=True,
        related_name="rapports",
        verbose_name="Vulnérabilités incluses"
    )
    titre = models.CharField(max_length=255, verbose_name="Titre du rapport")
    format = models.CharField(
        max_length=10,
        choices=FormatRapport.choices,
        default=FormatRapport.PDF,
        verbose_name="Format d'export"
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutRapport.choices,
        default=StatutRapport.BROUILLON,
        verbose_name="Statut du rapport"
    )
    cheminFichier = models.CharField(max_length=255, blank=True, default="", verbose_name="Chemin du fichier généré")
    scoreFinal = models.FloatField(default=0.0, verbose_name="Score de sécurité final (0 à 100)")
    dateGeneration = models.DateTimeField(auto_now_add=True, verbose_name="Date de génération")

    class Meta:
        verbose_name = "Rapport d'Évaluation"
        verbose_name_plural = "Rapports d'Évaluation"
        ordering = ['-dateGeneration']

    def __str__(self):
        return f"Rapport [{self.format}] {self.titre} - Score: {self.scoreFinal}/100 ({self.get_statut_display()})"

    def generer(self):
        """
        Méthode métier generer() :
        Associe les vulnérabilités de l'audit, capture le scoreSecurite final,
        génère le contenu et enregistre le fichier sur disque.
        """
        self.audit.calculerScore()
        self.scoreFinal = self.audit.scoreSecurite
        self.statut = StatutRapport.EN_REVISION

        # Lier toutes les vulnérabilités de l'audit
        vulns = self.audit.vulnerabilites.all()
        self.save()
        self.vulnerabilites.set(vulns)

        # Générer le fichier
        dir_path = os.path.join(settings.BASE_DIR, 'media', 'reports')
        os.makedirs(dir_path, exist_ok=True)
        ext = self.format.lower()
        filename = f"rapport_audit_{self.audit.id}_{self.id}.{ext}"
        filepath = os.path.join(dir_path, filename)

        if self.format == FormatRapport.JSON:
            content = {
                'rapport_id': str(self.id),
                'titre': self.titre,
                'score_final': self.scoreFinal,
                'cible': self.audit.cible.valeur,
                'date_generation': timezone.now().isoformat(),
                'vulnerabilites': [
                    {
                        'titre': v.titre,
                        'gravite': v.gravite,
                        'score_cvss': v.scoreCVSS,
                        'cwe': v.codeCWE,
                        'statut': v.statut
                    }
                    for v in vulns
                ]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)

        elif self.format == FormatRapport.CSV:
            lines = ["Titre,Gravite,ScoreCVSS,CWE,Statut\n"]
            for v in vulns:
                lines.append(f'"{v.titre}","{v.gravite}",{v.scoreCVSS},"{v.codeCWE}","{v.statut}"\n')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        elif self.format == FormatRapport.HTML:
            from .pdf_generator import generate_html_report
            generate_html_report(self, filepath)

        elif self.format == FormatRapport.PDF:
            from .pdf_generator import generate_pdf_report
            generate_pdf_report(self, filepath)

        self.cheminFichier = filepath
        self.save(update_fields=['scoreFinal', 'statut', 'cheminFichier'])
        return self

    def valider(self):
        """Méthode métier valider() : passe le statut en VALIDE."""
        self.statut = StatutRapport.VALIDE
        self.save(update_fields=['statut'])
        return self

    def publier(self):
        """Méthode métier publier() : passe le statut en PUBLIE."""
        self.statut = StatutRapport.PUBLIE
        self.save(update_fields=['statut'])
        return self

    def telecharger(self):
        """Méthode métier telecharger() : renvoie le contenu binaire ou texte du fichier généré."""
        if not self.cheminFichier or not os.path.exists(self.cheminFichier):
            self.generer()

        if self.format == FormatRapport.PDF:
            with open(self.cheminFichier, 'rb') as f:
                return f.read()
        else:
            with open(self.cheminFichier, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
