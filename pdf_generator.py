import os
import io
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

# Font Setup for Indian scripts support
has_indic_fonts = False

def setup_indic_fonts():
    global has_indic_fonts
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    font_paths = {
        "FreeSans": os.path.join(font_dir, "FreeSans.ttf"),
        "FreeSansBold": os.path.join(font_dir, "FreeSansBold.ttf"),
        "FreeSansOblique": os.path.join(font_dir, "FreeSansOblique.ttf")
    }
    
    urls = {
        "FreeSans": "https://raw.githubusercontent.com/fedora-infra/freefont/master/FreeSans.ttf",
        "FreeSansBold": "https://raw.githubusercontent.com/fedora-infra/freefont/master/FreeSansBold.ttf",
        "FreeSansOblique": "https://raw.githubusercontent.com/fedora-infra/freefont/master/FreeSansOblique.ttf"
    }

    downloaded = True
    for name, path in font_paths.items():
        if not os.path.exists(path):
            import requests
            try:
                print(f"Downloading {name}.ttf for multi-language PDF support...", flush=True)
                r = requests.get(urls[name], timeout=30)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    print(f"Downloaded {name}.ttf successfully.", flush=True)
                else:
                    print(f"Failed to download {name}.ttf: HTTP {r.status_code}", flush=True)
                    downloaded = False
            except Exception as e:
                print(f"Error downloading {name}.ttf: {e}", flush=True)
                downloaded = False
        
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception as re:
                print(f"Error registering font {name}: {re}", flush=True)
                downloaded = False
                
    has_indic_fonts = downloaded

# Try running setup on import
try:
    setup_indic_fonts()
except Exception as e:
    print(f"Indic font setup failed on load: {e}")


def load_pdf_translations(lang_code):
    translations = {}
    translations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations")
    
    # Load English fallback first
    en_path = os.path.join(translations_dir, "en.json")
    if os.path.exists(en_path):
        try:
            with open(en_path, "r", encoding="utf-8") as f:
                translations.update(json.load(f))
        except Exception as e:
            print(f"Error loading English fallback translations: {e}")
            
    # Load selected language
    if lang_code and lang_code != "en":
        lang_path = os.path.join(translations_dir, f"{lang_code}.json")
        if os.path.exists(lang_path):
            try:
                with open(lang_path, "r", encoding="utf-8") as f:
                    translations.update(json.load(f))
            except Exception as e:
                print(f"Error loading {lang_code} translations: {e}")
                
    return translations


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically track and print the total page count
    along with professional footer branding on every page.
    """
    language = "en"
    translations = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        font_name = "FreeSans" if has_indic_fonts else "Helvetica"
        self.setFont(font_name, 8)
        self.setFillColor(HexColor("#4B5563")) # gray-600
        
        def translate_canvas(key, default):
            return NumberedCanvas.translations.get(key, default)
        
        # 1. Header decoration (only on page 2 and later)
        if self._pageNumber > 1:
            title_text = translate_canvas("pdf.report_title", "AI Crop Disease Analysis Report")
            subtitle_text = translate_canvas("pdf.report_subtitle", "CropDiseaseAI Diagnostics")
            self.drawString(36, 805, title_text)
            self.drawRightString(559, 805, subtitle_text)
            self.setStrokeColor(HexColor("#E5E7EB")) # gray-200
            self.setLineWidth(0.5)
            self.line(36, 798, 559, 798)
            
        # 2. Footer decoration (on all pages)
        self.setStrokeColor(HexColor("#E5E7EB")) # gray-200
        self.setLineWidth(0.5)
        self.line(36, 45, 559, 45)
        
        footer_brand = translate_canvas("pdf.footer_branding", "Generated by CropDiseaseAI | Confidential Diagnostic Report")
        self.drawString(36, 30, footer_brand)
        
        page_str_template = translate_canvas("pdf.page_num_text", "Page {page_num} of {total_pages}")
        page_str = page_str_template.format(page_num=self._pageNumber, total_pages=page_count)
        self.drawRightString(559, 30, page_str)
        
        self.restoreState()


def generate_pdf_report(data, username=None):
    """
    Generates a professional A4 PDF bytes buffer from analysis results.
    Supports single dictionary report or list/collection of reports.
    """
    # Load translations & register to canvas
    lang = "en"
    if isinstance(data, dict):
        lang = data.get("language", "en")
    elif isinstance(data, list) and len(data) > 0:
        lang = data[0].get("language", "en")
        
    translations = load_pdf_translations(lang)
    NumberedCanvas.language = lang
    NumberedCanvas.translations = translations

    # Check if this is a bulk reports compilation
    if isinstance(data, list):
        reports_list = data
    elif isinstance(data, dict) and "reports" in data:
        reports_list = data["reports"]
    else:
        reports_list = [data]

    # Setup Document Layout
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=64
    )
    
    # Design System & Typography
    PRIMARY_GREEN = HexColor("#15803D")   # Green 700
    LIGHT_GREEN = HexColor("#F0FDF4")     # Green 50
    TEXT_DARK = HexColor("#1F2937")       # Gray 800
    TEXT_MUTED = HexColor("#4B5563")      # Gray 600
    BORDER_COLOR = HexColor("#86EFAC")    # Green 300
    
    font_regular = "FreeSans" if has_indic_fonts else "Helvetica"
    font_bold = "FreeSansBold" if has_indic_fonts else "Helvetica-Bold"
    font_oblique = "FreeSansOblique" if has_indic_fonts else "Helvetica-Oblique"

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=18,
        leading=22,
        textColor=PRIMARY_GREEN,
        spaceAfter=2
    )
    
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=PRIMARY_GREEN,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    subsection_heading = ParagraphStyle(
        "SubsectionHeading",
        parent=styles["Heading3"],
        fontName=font_bold,
        fontSize=10,
        leading=14,
        textColor=TEXT_DARK,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "BodyTextDark",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_DARK,
        spaceAfter=4
    )
    
    body_bold = ParagraphStyle(
        "BodyTextBold",
        parent=body_style,
        fontName=font_bold
    )
    
    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName=font_oblique,
        fontSize=8,
        leading=11.5,
        textColor=TEXT_MUTED,
        spaceBefore=6
    )

    story = []

    for r_idx, report in enumerate(reports_list):
        # Parse current report data
        crop_name = report.get("crop_name", "N/A")
        disease_name = report.get("disease_name", "N/A")
        
        # Translate confidence & severity values in PDF
        confidence_val = report.get("confidence", "N/A")
        confidence_key = f"confidence.{confidence_val.lower()}"
        confidence = translations.get(confidence_key, confidence_val)

        severity_val = report.get("severity", "N/A")
        severity_key = f"severity.{severity_val.lower()}"
        severity = translations.get(severity_key, severity_val)

        symptoms = report.get("symptoms", [])
        possible_causes = report.get("possible_causes", [])
        prevention = report.get("prevention", [])
        treatment = report.get("treatment", [])
        fertilizer = report.get("fertilizer_recommendation", "No custom fertilizer recommendations available.")
        watering = report.get("watering_advice", "No custom watering advice available.")
        notes = report.get("additional_notes", "No additional notes provided.")
        filename = report.get("filename", "")
        treatment_guidance = report.get("treatment_guidance", None)
        calculator_metrics = report.get("calculator_metrics", None)

        # Logo & Banner Header
        logo_path = "static/images/logo.png"
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=42, height=42)
        else:
            logo_img = Paragraph("🌱", ParagraphStyle("LogoText", fontName=font_regular, fontSize=28, leading=32))
            
        title_text = f"<b>{translations.get('pdf.report_title', 'AI Crop Disease Analysis Report')}</b><br/><font size=8.5 color='#4B5563'>{translations.get('pdf.report_subtitle', 'Generated by CropDiseaseAI Diagnostics')}</font>"
        title_p = Paragraph(title_text, title_style)
        
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_html = f"<b>{translations.get('pdf.date', 'Date')}:</b> {date_str}<br/><b>{translations.get('pdf.prepared_for', 'Prepared For')}:</b> {username or 'Guest User'}"
        meta_p = Paragraph(meta_html, body_style)
        
        header_table = Table([[logo_img, title_p, meta_p]], colWidths=[55, 300, 168])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(header_table)
        
        # Header Accent line
        divider = Table([[""]], colWidths=[523], rowHeights=[2])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), PRIMARY_GREEN),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(divider)
        story.append(Spacer(1, 12))

        # General Information & Leaf Image Card
        details_data = [
            [Paragraph(f"<b>{translations.get('pdf.crop_name', 'Crop Name')}:</b>", body_style), Paragraph(crop_name, body_style)],
            [Paragraph(f"<b>{translations.get('pdf.disease_identified', 'Disease Identified')}:</b>", body_style), Paragraph(disease_name, body_style)],
            [Paragraph(f"<b>{translations.get('pdf.confidence_level', 'Confidence Level')}:</b>", body_style), Paragraph(confidence, body_style)],
            [Paragraph(f"<b>{translations.get('pdf.severity_level', 'Severity Level')}:</b>", body_style), Paragraph(severity, body_style)],
        ]
        details_table = Table(details_data, colWidths=[110, 190])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        
        # Scale Leaf Image keeping aspect ratio
        img_path = f"uploads/{filename}"
        if filename and os.path.exists(img_path):
            try:
                with PILImage.open(img_path) as pil_img:
                    w, h = pil_img.size
                    aspect = w / h
                    if aspect >= 4/3:
                        img_w = 180
                        img_h = int(180 / aspect)
                    else:
                        img_h = 135
                        img_w = int(135 * aspect)
                report_img = Image(img_path, width=img_w, height=img_h)
            except Exception:
                report_img = Paragraph("<i>[Leaf Image Uploaded]</i>", body_style)
        else:
            report_img = Paragraph("<i>[No leaf image uploaded]</i>", body_style)

        # Nest Details & Image inside a styled card Table
        summary_data = [[details_table, report_img]]
        summary_table = Table(summary_data, colWidths=[310, 213])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,-1), LIGHT_GREEN),
            ('BOX', (0,0), (-1,-1), 0.75, BORDER_COLOR),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # Diagnosis Section: Symptoms & Causes side-by-side
        story.append(Paragraph(translations.get('pdf.diagnostic_details', 'Diagnostic Finding Details'), section_heading))
        
        symptom_bullets = "".join([f"• {s}<br/>" for s in symptoms]) if symptoms else "• None described."
        cause_bullets = "".join([f"• {c}<br/>" for c in possible_causes]) if possible_causes else "• None described."
        
        diag_data = [
            [Paragraph(f"<b>🔍 {translations.get('pdf.observed_symptoms', 'Observed Symptoms')}:</b>", body_bold), Paragraph(f"<b>⚠️ {translations.get('pdf.possible_causes', 'Possible Causes')}:</b>", body_bold)],
            [Paragraph(symptom_bullets, body_style), Paragraph(cause_bullets, body_style)]
        ]
        diag_table = Table(diag_data, colWidths=[256, 267])
        diag_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), HexColor("#FAFAFA")),
            ('LINEBELOW', (0,0), (1,0), 0.5, HexColor("#E5E7EB")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(diag_table)
        story.append(Spacer(1, 10))

        # Management & Action Plan
        story.append(Paragraph(translations.get('pdf.management_recommendations', 'Agricultural Recommendations'), section_heading))
        
        prevention_bullets = "".join([f"• {p}<br/>" for p in prevention]) if prevention else "• None described."
        treatment_bullets = "".join([f"• {t}<br/>" for t in treatment]) if treatment else "• None described."
        
        action_data = [
            [Paragraph(f"<b>🛡️ {translations.get('pdf.prevention_measures', 'Prevention Measures')}:</b>", body_bold), Paragraph(f"<b>💊 {translations.get('pdf.recommended_treatments', 'Recommended Treatments')}:</b>", body_bold)],
            [Paragraph(prevention_bullets, body_style), Paragraph(treatment_bullets, body_style)]
        ]
        action_table = Table(action_data, colWidths=[256, 267])
        action_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), HexColor("#FAFAFA")),
            ('LINEBELOW', (0,0), (1,0), 0.5, HexColor("#E5E7EB")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(action_table)
        story.append(Spacer(1, 10))

        # Nutrients, Watering & Additional Notes
        notes_data = [
            [Paragraph(f"<b>🧪 {translations.get('pdf.fertilizer_recommendation', 'Fertilizer Recommendation')}:</b>", body_bold), Paragraph(fertilizer, body_style)],
            [Paragraph(f"<b>💧 {translations.get('pdf.water_advice', 'Irrigation & Water Advice')}:</b>", body_bold), Paragraph(watering, body_style)],
            [Paragraph(f"<b>📝 {translations.get('pdf.additional_notes', 'Additional Notes')}:</b>", body_bold), Paragraph(notes, body_style)],
        ]
        notes_table = Table(notes_data, colWidths=[150, 373])
        notes_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 10))

        # Verified Treatment Guidance Section (if available)
        if treatment_guidance:
            tg_elements = []
            tg_elements.append(Paragraph(translations.get('pdf.verified_treatment_guidance', 'Verified Agricultural Treatment Guidance'), section_heading))
            
            # Organic step block
            if treatment_guidance.get("organic_treatment"):
                tg_elements.append(Paragraph(f"<b>{translations.get('pdf.organic_protocol', 'Organic Treatment Protocol')}:</b>", subsection_heading))
                for idx, step in enumerate(treatment_guidance.get("organic_treatment")):
                    tg_elements.append(Paragraph(f"<b>Step {idx+1}:</b> {step}", body_style))
                if treatment_guidance.get("alternative_organic_solutions"):
                    tg_elements.append(Paragraph(f"<i>{translations.get('pdf.organic_alternatives', 'Organic Alternatives')}:</i> {treatment_guidance.get('alternative_organic_solutions')}", body_style))
                tg_elements.append(Spacer(1, 6))

            # Chemical medicine table
            if treatment_guidance.get("chemical_treatment_name"):
                tg_elements.append(Paragraph(f"<b>{translations.get('pdf.chemical_treatment_dosage', 'Chemical Treatment & Dosage Plan')}:</b>", subsection_heading))
                
                equip_text = translations.get('pdf.dissolve_text', 'Dissolve {mixing_quantity} in {water_quantity} of water.').format(
                    mixing_quantity=treatment_guidance.get('mixing_quantity', 'N/A'),
                    water_quantity=treatment_guidance.get('water_quantity', '15 Litres')
                )
                
                timing_text = translations.get('pdf.timing_text', 'Apply at {spray_timing}. Repeat after {spray_interval} as required (Max {number_of_applications} applications).').format(
                    spray_timing=treatment_guidance.get('spray_timing', 'N/A'),
                    spray_interval=treatment_guidance.get('spray_interval', 'N/A'),
                    number_of_applications=treatment_guidance.get('number_of_applications', 'N/A')
                )
                
                safety_text = translations.get('pdf.safety_text', 'Harvest wait time: {waiting_period_before_harvest}. PPE Required: {ppe_required}.').format(
                    waiting_period_before_harvest=treatment_guidance.get('waiting_period_before_harvest', 'N/A'),
                    ppe_required=treatment_guidance.get('ppe_required', 'N/A')
                )
                
                chem_rows = [
                    [Paragraph(f"<b>{translations.get('pdf.medicine_name', 'Medicine Name')}:</b>", body_style), Paragraph(treatment_guidance.get("chemical_treatment_name"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.active_ingredient', 'Active Ingredient')}:</b>", body_style), Paragraph(treatment_guidance.get("active_ingredient", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.brand_examples', 'Common Brand Examples')}:</b>", body_style), Paragraph(treatment_guidance.get("example_brand_names", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.application_method', 'Application Method')}:</b>", body_style), Paragraph(treatment_guidance.get("application_method", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.spray_equipment_base', 'Spray Equipment Base')}:</b>", body_style), Paragraph(equip_text, body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.timing_intervals', 'Timing & Frequency')}:</b>", body_style), Paragraph(timing_text, body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.safety_waiting_period', 'Safety & Harvest Waiting Period')}:</b>", body_style), Paragraph(safety_text, body_style)],
                ]
                chem_table = Table(chem_rows, colWidths=[140, 383])
                chem_table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                ]))
                tg_elements.append(chem_table)
                tg_elements.append(Spacer(1, 6))

            # Sprayer Calibration Metrics
            if calculator_metrics:
                tg_elements.append(Paragraph(f"<b>{translations.get('pdf.sprayer_field_plan', 'Sprayer Calibration & Field Plan')}:</b>", subsection_heading))
                
                tank_mix_text = translations.get('pdf.per_tank_mix_text', 'Mix {per_tank_dosage} per tank (Capacity: {tank_capacity} L).').format(
                    per_tank_dosage=calculator_metrics.get('per_tank_dosage', 'N/A'),
                    tank_capacity=calculator_metrics.get('tank_capacity')
                )
                
                costs_text = translations.get('pdf.costs_text', 'Medicine: {cost_medicine} | Labor: {cost_labour} | Total: {cost_total}').format(
                    cost_medicine=calculator_metrics.get('cost_medicine', 'N/A'),
                    cost_labour=calculator_metrics.get('cost_labour', 'N/A'),
                    cost_total=calculator_metrics.get('cost_total', 'N/A')
                )
                
                metrics_rows = [
                    [Paragraph(f"<b>{translations.get('pdf.land_size', 'Land Size')}:</b>", body_style), Paragraph(f"{calculator_metrics.get('land_size')} {calculator_metrics.get('land_unit')}", body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.total_field_medicine', 'Total Field Medicine')}:</b>", body_style), Paragraph(calculator_metrics.get("total_medicine", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.total_field_water', 'Total Field Water')}:</b>", body_style), Paragraph(calculator_metrics.get("total_water", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.sprayer_runs', 'Sprayer Runs')}:</b>", body_style), Paragraph(calculator_metrics.get("tanks_count", "N/A"), body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.per_tank_dosage', 'Per-Tank Mix Dosage')}:</b>", body_style), Paragraph(tank_mix_text, body_style)],
                    [Paragraph(f"<b>{translations.get('pdf.estimated_costs', 'Estimated Costs')}:</b>", body_style), Paragraph(costs_text, body_style)],
                ]
                metrics_table = Table(metrics_rows, colWidths=[140, 383])
                metrics_table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                ]))
                tg_elements.append(metrics_table)
                tg_elements.append(Spacer(1, 6))

            # Advisory source
            source = treatment_guidance.get("government_advisory_source")
            updated = treatment_guidance.get("last_updated_date")
            if source:
                tg_elements.append(Paragraph(translations.get('pdf.source_text', 'Source: {source} | Last Updated: {updated_date}').format(source=source, updated_date=updated or 'N/A'), disclaimer_style))
                
            story.append(KeepTogether(tg_elements))
            story.append(Spacer(1, 10))

        # AI Disclaimer Block
        disclaimer_elements = []
        disclaimer_elements.append(Paragraph(f"<b>{translations.get('pdf.ai_disclaimer_title', 'AI Diagnostics Disclaimer')}:</b>", body_bold))
        disclaimer_text = translations.get('pdf.ai_disclaimer_text', '')
        disclaimer_elements.append(Paragraph(disclaimer_text, disclaimer_style))
        story.append(KeepTogether(disclaimer_elements))

        # If there are more reports in the list, append a PageBreak to separate pages
        if r_idx < len(reports_list) - 1:
            story.append(PageBreak())

    # Build PDF document
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
