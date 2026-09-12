"""
Module de génération de rapports PDF et HTML pour SecEval AI.
Produit des fichiers PDF binaires valides (ReportLab ou Pure-Python PDF Builder)
et des fichiers HTML lisibles et stylisés.
"""
import os
import re
import html
from django.utils import timezone

try:
    import markdown
except ImportError:
    markdown = None

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def markdown_to_html(text):
    """
    Convertit la syntaxe Markdown en HTML structuré.
    """
    if not text:
        return "<p><em>Aucun contenu de rapport disponible.</em></p>"

    cleaned_text = re.sub(
        r'`?\s*┌─+┐[\s\S]*?└─+┘\s*`?',
        _replace_ascii_box,
        str(text),
        flags=re.IGNORECASE
    )

    if markdown:
        try:
            return markdown.markdown(
                cleaned_text,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        except Exception:
            pass

    return _simple_markdown_fallback(cleaned_text)


def _replace_ascii_box(match):
    content = match.group(0)
    score_m = re.search(r'SCORE GLOBAL\s*:\s*([\d\.]+\s*\/\s*10[^\n\|]*)', content, re.I)
    score_str = score_m.group(1).strip() if score_m else "Évalué"

    c_m = re.search(r'Critique\s*:\s*(\d+)', content, re.I)
    e_m = re.search(r'Élevé\s*:\s*(\d+)', content, re.I)
    m_m = re.search(r'Moyen\s*:\s*(\d+)', content, re.I)
    f_m = re.search(r'Faible\s*:\s*(\d+)', content, re.I)

    c_cnt = c_m.group(1) if c_m else '0'
    e_cnt = e_m.group(1) if e_m else '0'
    m_cnt = m_m.group(1) if m_m else '0'
    f_cnt = f_m.group(1) if f_m else '0'

    return f"""
<div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px; margin: 16px 0; color: #f8fafc;">
    <div style="font-weight: 700; font-size: 1.1rem; color: #38bdf8; margin-bottom: 10px;">
        📊 SCORE GLOBAL : <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; color: #ffffff;">{score_str}</span>
    </div>
    <div style="display: flex; gap: 10px; font-size: 0.9rem;">
        <span style="background: rgba(220,38,38,0.3); color: #f87171; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🔴 Critique: {c_cnt}</span>
        <span style="background: rgba(239,68,68,0.2); color: #fca5a5; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🔴 Élevé: {e_cnt}</span>
        <span style="background: rgba(245,158,11,0.2); color: #fde047; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🟡 Moyen: {m_cnt}</span>
        <span style="background: rgba(34,197,94,0.2); color: #86efac; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🟢 Faible: {f_cnt}</span>
    </div>
</div>
"""


def _simple_markdown_fallback(text):
    lines = text.splitlines()
    out = []
    in_table = False
    table_headers = []
    table_rows = []

    for line in lines:
        sline = line.strip()
        if sline.startswith('|') and sline.endswith('|'):
            cells = [c.strip() for c in sline.split('|')[1:-1]]
            if not in_table:
                in_table = True
                table_headers = cells
                continue
            if '---' in sline:
                continue
            table_rows.append(cells)
        else:
            if in_table:
                out.append(_render_html_table(table_headers, table_rows))
                in_table = False
                table_headers, table_rows = [], []

            if sline.startswith('### '):
                out.append(f"<h4>{html.escape(sline[4:])}</h4>")
            elif sline.startswith('## '):
                out.append(f"<h3>{html.escape(sline[3:])}</h3>")
            elif sline.startswith('# '):
                out.append(f"<h2>{html.escape(sline[2:])}</h2>")
            elif sline == '---':
                out.append("<hr>")
            elif sline:
                formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html.escape(sline))
                formatted = re.sub(r'`(.*?)`', r'<code>\1</code>', formatted)
                out.append(f"<p>{formatted}</p>")

    if in_table:
        out.append(_render_html_table(table_headers, table_rows))

    return "\n".join(out)


def _render_html_table(headers, rows):
    th_html = "".join([f"<th>{html.escape(h)}</th>" for h in headers])
    tr_html = ""
    for r in rows:
        td_html = "".join([f"<td>{html.escape(c)}</td>" for c in r])
        tr_html += f"<tr>{td_html}</tr>"
    return f"<table border='1' style='border-collapse:collapse; width:100%; margin:10px 0;'><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table>"


class NumberedCanvas(canvas.Canvas if REPORTLAB_AVAILABLE else object):
    """Canvas personnalisé pour ajouter les numéros de page et le pied de page."""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))

        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 45, 555, 45)

        self.drawString(40, 30, "SecEval AI — Rapport d'Évaluation de Sécurité Confidentiel")
        page_str = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(555, 30, page_str)
        self.restoreState()


def generate_html_report(rapport_obj, filepath, report_text=None):
    """
    Génère un fichier HTML complet, autonome et stylisé pour l'impression ou la lecture Web.
    """
    audit = rapport_obj.audit
    titre = rapport_obj.titre or f"Rapport d'Évaluation - {audit.cible.valeur}"
    score = rapport_obj.scoreFinal
    date_str = rapport_obj.dateGeneration.strftime('%d/%m/%Y à %H:%M') if rapport_obj.dateGeneration else timezone.now().strftime('%d/%m/%Y à %H:%M')
    cible_val = audit.cible.valeur if audit.cible else "N/A"

    raw_text = report_text or (audit.resultatBrutN8n.get('rapport') if isinstance(audit.resultatBrutN8n, dict) else None)
    if not raw_text:
        raw_text = audit.contexte or "Aucune analyse disponible."

    body_html = markdown_to_html(raw_text)

    vulns = rapport_obj.vulnerabilites.all() if rapport_obj.pk else audit.vulnerabilites.all()
    vulns_table_rows = ""
    for v in vulns:
        badge_class = "critique" if v.gravite == "CRITIQUE" else ("eleve" if v.gravite == "ELEVE" else ("moyen" if v.gravite == "MOYEN" else "faible"))
        vulns_table_rows += f"""
        <tr>
            <td><strong>{html.escape(v.titre)}</strong></td>
            <td><span class="badge {badge_class}">{html.escape(v.gravite)}</span></td>
            <td>{v.scoreCVSS}</td>
            <td>{html.escape(v.codeCWE or 'N/A')}</td>
            <td>{html.escape(v.statut)}</td>
        </tr>
        """

    vulns_section = ""
    if vulns.exists():
        vulns_section = f"""
        <h2>🛡️ Vulnérabilités Détectées ({vulns.count()})</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Intitulé</th>
                    <th>Gravité</th>
                    <th>CVSS</th>
                    <th>CWE</th>
                    <th>Statut</th>
                </tr>
            </thead>
            <tbody>
                {vulns_table_rows}
            </tbody>
        </table>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(titre)}</title>
    <style>
        :root {{
            --primary: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --accent: #38bdf8;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background-color: var(--primary);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 30px;
        }}
        .report-header {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .header-title {{
            margin: 0 0 10px 0;
            color: var(--accent);
            font-size: 1.8rem;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        .meta-item {{
            background: #0f172a;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .meta-item small {{
            color: #94a3b8;
            text-transform: uppercase;
            font-size: 0.75rem;
            display: block;
        }}
        .meta-item strong {{
            font-size: 1.1rem;
            color: #ffffff;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.85rem;
        }}
        .critique {{ background: rgba(220, 38, 38, 0.3); color: #f87171; border: 1px solid #ef4444; }}
        .eleve {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; }}
        .moyen {{ background: rgba(245, 158, 11, 0.2); color: #fde047; }}
        .faible {{ background: rgba(34, 197, 94, 0.2); color: #86efac; }}
        
        .content-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 28px;
            margin-bottom: 24px;
        }}
        .content-card h1, .content-card h2, .content-card h3 {{
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }}
        .data-table th, .data-table td {{
            padding: 12px;
            border: 1px solid var(--border);
            text-align: left;
        }}
        .data-table th {{
            background-color: #334155;
            color: #ffffff;
        }}
        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .report-header, .content-card {{ background: #ffffff; border: 1px solid #cccccc; color: #000000; }}
            .meta-item {{ background: #f8fafc; border-color: #cccccc; color: #000000; }}
            .meta-item strong {{ color: #000000; }}
            .content-card h1, .content-card h2, .content-card h3 {{ color: #0284c7; border-bottom-color: #cccccc; }}
            .data-table th {{ background-color: #f1f5f9; color: #000000; }}
            .data-table th, .data-table td {{ border-color: #cccccc; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1 class="header-title">🛡️ {html.escape(titre)}</h1>
        <div class="meta-grid">
            <div class="meta-item">
                <small>Cible d'évaluation</small>
                <strong>{html.escape(cible_val)}</strong>
            </div>
            <div class="meta-item">
                <small>Score de Sécurité</small>
                <strong style="color: {'#22c55e' if score >= 80 else ('#f59e0b' if score >= 50 else '#ef4444')};">{score}/100</strong>
            </div>
            <div class="meta-item">
                <small>Date de Génération</small>
                <strong>{date_str}</strong>
            </div>
            <div class="meta-item">
                <small>Type d'Audit</small>
                <strong>{html.escape(audit.get_type_display() if hasattr(audit, 'get_type_display') else audit.type)}</strong>
            </div>
        </div>
    </div>

    {f'<div class="content-card">{vulns_section}</div>' if vulns_section else ''}

    <div class="content-card">
        <h2>📋 Analyse Détaillée & Recommandations SecEval AI</h2>
        {body_html}
    </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_html)
    return filepath


def generate_pdf_report(rapport_obj, filepath, report_text=None):
    """
    Génère un véritable fichier PDF binaire structuré (`%PDF-1.4`).
    Utilise ReportLab si présent, sinon utilise le générateur PDF binaire autonome d'urgence.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if REPORTLAB_AVAILABLE:
        try:
            return _generate_reportlab_pdf(rapport_obj, filepath, report_text)
        except Exception as e:
            print(f"[ReportLab Error] {e}. Utilisation du générateur PDF binaire autonome...")

    return _generate_pure_python_pdf(rapport_obj, filepath, report_text)


def _generate_reportlab_pdf(rapport_obj, filepath, report_text=None):
    audit = rapport_obj.audit
    titre = rapport_obj.titre or f"Rapport d'Évaluation - {audit.cible.valeur}"
    score = float(rapport_obj.scoreFinal)
    date_str = rapport_obj.dateGeneration.strftime('%d/%m/%Y à %H:%M') if rapport_obj.dateGeneration else timezone.now().strftime('%d/%m/%Y à %H:%M')
    cible_val = audit.cible.valeur if audit.cible else "N/A"

    raw_text = report_text or (audit.resultatBrutN8n.get('rapport') if isinstance(audit.resultatBrutN8n, dict) else None)
    if not raw_text:
        raw_text = audit.contexte or "Aucune analyse détaillée fournie."

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor("#0f172a"), spaceAfter=15)
    subtitle_style = ParagraphStyle('ReportSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor("#64748b"), spaceAfter=20)
    h2_style = ParagraphStyle('ReportH2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor("#0284c7"), spaceBefore=15, spaceAfter=10, keepWithNext=True)
    h3_style = ParagraphStyle('ReportH3', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor("#334155"), spaceBefore=10, spaceAfter=6, keepWithNext=True)
    body_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor("#1e293b"), spaceAfter=8)

    meta_label_style = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#475569"))
    meta_val_style = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#0f172a"))

    story = []

    story.append(Paragraph(f"🛡️ {html.escape(titre)}", title_style))
    story.append(Paragraph("Plateforme de Red Teaming & Évaluation Automatisée de Sécurité — SecEval AI", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#38bdf8"), spaceAfter=15))

    score_color = colors.HexColor("#16a34a") if score >= 80 else (colors.HexColor("#d97706") if score >= 50 else colors.HexColor("#dc2626"))
    
    meta_data = [
        [
            Paragraph("<b>Cible :</b>", meta_label_style),
            Paragraph(html.escape(cible_val), meta_val_style),
            Paragraph("<b>Score de Sécurité :</b>", meta_label_style),
            Paragraph(f"<font color='{score_color.hexval()}'><b>{score} / 100</b></font>", meta_val_style)
        ],
        [
            Paragraph("<b>Type d'Audit :</b>", meta_label_style),
            Paragraph(html.escape(audit.get_type_display() if hasattr(audit, 'get_type_display') else audit.type), meta_val_style),
            Paragraph("<b>Date de Génération :</b>", meta_label_style),
            Paragraph(date_str, meta_val_style)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[100, 160, 110, 145])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    vulns = rapport_obj.vulnerabilites.all() if rapport_obj.pk else audit.vulnerabilites.all()
    if vulns.exists():
        story.append(Paragraph("🛡️ Synthèse des Vulnérabilités Détectées", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

        vuln_headers = [
            Paragraph("<b>Intitulé</b>", meta_label_style),
            Paragraph("<b>Gravité</b>", meta_label_style),
            Paragraph("<b>CVSS</b>", meta_label_style),
            Paragraph("<b>CWE</b>", meta_label_style),
            Paragraph("<b>Statut</b>", meta_label_style)
        ]
        vtable_data = [vuln_headers]

        for v in vulns:
            grav_color = "#dc2626" if v.gravite == "CRITIQUE" else ("#ea580c" if v.gravite == "ELEVE" else ("#d97706" if v.gravite == "MOYEN" else "#16a34a"))
            vtable_data.append([
                Paragraph(html.escape(v.titre), body_style),
                Paragraph(f"<font color='{grav_color}'><b>{html.escape(v.gravite)}</b></font>", body_style),
                Paragraph(str(v.scoreCVSS), body_style),
                Paragraph(html.escape(v.codeCWE or 'N/A'), body_style),
                Paragraph(html.escape(v.statut), body_style)
            ])

        vuln_table = Table(vtable_data, colWidths=[200, 75, 50, 95, 95])
        vuln_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(vuln_table)
        story.append(Spacer(1, 15))

    story.append(Paragraph("📋 Analyse Détaillée de l'Agent IA", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    lines = str(raw_text).splitlines()
    in_code = False
    code_lines = []

    for line in lines:
        sline = line.strip()

        if sline.startswith('```'):
            if in_code:
                code_text = "<br/>".join([html.escape(cl) for cl in code_lines])
                story.append(Paragraph(f"<font face='Courier' size=8 color='#0f172a'>{code_text}</font>", body_style))
                story.append(Spacer(1, 6))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(sline)
            continue

        if not sline:
            story.append(Spacer(1, 4))
            continue

        if sline.startswith('### '):
            story.append(Paragraph(html.escape(sline[4:]), h3_style))
        elif sline.startswith('## '):
            story.append(Paragraph(html.escape(sline[3:]), h2_style))
        elif sline.startswith('# '):
            story.append(Paragraph(html.escape(sline[2:]), h2_style))
        elif sline.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        else:
            formatted = html.escape(sline)
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<font face="Courier" size=8.5 color="#0284c7">\1</font>', formatted)
            story.append(Paragraph(formatted, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return filepath


def _generate_pure_python_pdf(rapport_obj, filepath, report_text=None):
    """
    Générateur PDF binaire pur Python (zéro dépendance externe).
    Écrit des structures d'objets PDF 1.4 valides (%PDF-1.4).
    """
    audit = rapport_obj.audit
    titre = rapport_obj.titre or f"Rapport d'Évaluation - {audit.cible.valeur}"
    score = rapport_obj.scoreFinal
    date_str = rapport_obj.dateGeneration.strftime('%d/%m/%Y à %H:%M') if rapport_obj.dateGeneration else timezone.now().strftime('%d/%m/%Y à %H:%M')
    cible_val = audit.cible.valeur if audit.cible else "N/A"

    raw_text = report_text or (audit.resultatBrutN8n.get('rapport') if isinstance(audit.resultatBrutN8n, dict) else None)
    if not raw_text:
        raw_text = audit.contexte or "Aucune analyse fournie."

    def pdf_escape(text):
        return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    lines_pdf = []
    lines_pdf.append("BT")
    lines_pdf.append("/F2 16 Tf 40 800 Td (SecEval AI - Rapport d'Evaluation) Tj")
    lines_pdf.append("/F1 10 Tf 0 -20 Td (" + pdf_escape(titre) + ") Tj")
    lines_pdf.append("0 -15 Td (Cible: " + pdf_escape(cible_val) + " | Score: " + str(score) + "/100 | Date: " + date_str + ") Tj")
    lines_pdf.append("0 -25 Td /F2 12 Tf (Analyse & Synthese de l'Agent IA:) Tj /F1 9 Tf")

    raw_lines = str(raw_text).splitlines()
    y_pos = 730
    for l in raw_lines[:35]: # Troncature propre pour rentrer sur 1-2 pages si pur PDF
        sl = l.strip()
        if not sl:
            continue
        clean_l = re.sub(r'[\*\#\`\|]', '', sl)
        lines_pdf.append(f"0 -14 Td ({pdf_escape(clean_l[:90])}) Tj")

    lines_pdf.append("ET")
    content_stream = "\n".join(lines_pdf).encode('utf-8')

    objects = []
    objects.append(b"%PDF-1.4\n")
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>\nendobj\n")
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    stream_obj = f"6 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode('utf-8') + content_stream + b"\nendstream\nendobj\n"
    objects.append(stream_obj)

    # Calcul de la table xref
    xref_offsets = []
    current_offset = 0
    for obj in objects:
        xref_offsets.append(current_offset)
        current_offset += len(obj)

    xref_start = current_offset
    xref_table = [f"xref\n0 7\n0000000000 65535 f \n".encode('utf-8')]
    for i in range(1, 7):
        xref_table.append(f"{xref_offsets[i]:010d} 00000 n \n".encode('utf-8'))

    trailer = f"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode('utf-8')

    with open(filepath, 'wb') as f:
        for obj in objects:
            f.write(obj)
        for x in xref_table:
            f.write(x)
        f.write(trailer)

    return filepath
