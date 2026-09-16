import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 widescreen slides
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette: Modern Navy / Teal / Emerald / Gold / Slate
    C_BG_DARK = RGBColor(15, 23, 42)      # #0F172A Dark Slate / Navy
    C_BG_LIGHT = RGBColor(248, 250, 252)  # #F8FAFC Off white
    C_PRIMARY = RGBColor(14, 116, 144)    # #0E7490 Cyan 700
    C_PRIMARY_LIGHT = RGBColor(6, 182, 212) # #06B6D4 Cyan 500
    C_ACCENT_BLUE = RGBColor(37, 99, 235) # #2563EB Royal Blue
    C_ACCENT_GREEN = RGBColor(16, 185, 129) # #10B981 Emerald
    C_ACCENT_GOLD = RGBColor(245, 158, 11) # #F59E0B Amber
    C_TEXT_DARK = RGBColor(15, 23, 42)    # #0F172A
    C_TEXT_MUTED = RGBColor(100, 116, 139) # #64748B Slate 500
    C_TEXT_LIGHT = RGBColor(255, 255, 255)
    C_CARD_BG = RGBColor(255, 255, 255)
    C_CARD_BORDER = RGBColor(226, 232, 240) # #E2E8F0
    C_CARD_DARK = RGBColor(30, 41, 59)    # #1E293B

    def add_bg(slide, dark=False):
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = C_BG_DARK if dark else C_BG_LIGHT
        bg_shape.line.fill.background()
        return bg_shape

    def add_header(slide, title_text, category_text="BACAPP2-QWEN", dark=False):
        # Category pill/subtitle
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_PRIMARY_LIGHT if dark else C_PRIMARY
        p_cat.font.name = "Segoe UI"

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.75))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = C_TEXT_LIGHT if dark else C_TEXT_DARK
        p_title.font.name = "Segoe UI"

    def add_card(slide, left, top, width, height, bg_color=C_CARD_BG, border_color=C_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        return card

    # ==========================================
    # SLIDE 1: Title Slide (Dark Theme)
    # ==========================================
    slide1 = prs.slides.add_slide(blank_layout)
    add_bg(slide1, dark=True)

    # Accent bar
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.15), Inches(3.8))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_PRIMARY_LIGHT
    bar.line.fill.background()

    # Title box
    tb = slide1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11.0), Inches(3.8))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "PROIECTUL BACAPP2-QWEN"
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = C_PRIMARY_LIGHT
    p0.font.name = "Segoe UI"
    p0.space_after = Pt(12)

    p1 = tf.add_paragraph()
    p1.text = "Platformă Inteligentă de Pregătire pentru Bacalaureat"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = C_TEXT_LIGHT
    p1.font.name = "Segoe UI"

    p2 = tf.add_paragraph()
    p2.text = "Knowledge Graphs, Modele Lingvistice Mari (LLM - Qwen), RAG & Evaluare Științifică Riguroasă"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(203, 213, 225)
    p2.font.name = "Segoe UI"
    p2.space_before = Pt(10)
    p2.space_after = Pt(28)

    p3 = tf.add_paragraph()
    p3.text = "• Scopul Proiectului  |  • Arhitectura & Tehnologii  |  • Metodologia de Cercetare & Evaluare"
    p3.font.size = Pt(13)
    p3.font.color.rgb = C_ACCENT_GOLD
    p3.font.name = "Segoe UI"

    # ==========================================
    # SLIDE 2: Contextul & Problematica (The Problem)
    # ==========================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_bg(slide2, dark=False)
    add_header(slide2, "Contextul Educațional și Provocările Învățării Tradiționale", "PROBLEMATICA ȘI NEVOIA DE INOVAȚIE")

    cards_data_s2 = [
        ("1. Memorarea Mecanică Tradițională", 
         "Elevii de liceu apelează frecvent la memorarea pe de rost a unor comentarii literare rigide, fără o înțelegere de profunzime a structurii operei, a relațiilor cauzale dintre evenimente sau a evoluției personajelor.", 
         C_PRIMARY),
        ("2. Halucinațiile LLM-urilor Generice", 
         "Modelele AI clasice (fără ancorare strictă în text) inventează scene, atribuie replici greșite și generează anacronisme literare, fiind nefiabile pentru pregătirea unui examen național strict cum este Bacalaureatul.", 
         C_ACCENT_BLUE),
        ("3. Lipsa de Personalizare și Interactivitate", 
         "Manuale și culegerile tipărite oferă un conținut static, fără feedback imediat, fără exerciții adaptate pe tipologii cognitive (cronologie, cauză-efect, asocieri) și fără asistență ghidată în redactarea eseurilor.", 
         C_ACCENT_GOLD)
    ]

    left_pos = Inches(0.8)
    width = Inches(3.64)
    height = Inches(4.8)
    for title, desc, col in cards_data_s2:
        add_card(slide2, left_pos, Inches(1.8), width, height)
        badge = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_pos, Inches(1.8), width, Inches(0.12))
        badge.fill.solid()
        badge.fill.fore_color.rgb = col
        badge.line.fill.background()

        tb = slide2.shapes.add_textbox(left_pos + Inches(0.3), Inches(2.2), width - Inches(0.6), height - Inches(0.6))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(17)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_DARK
        p_t.space_after = Pt(14)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(13.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        left_pos += width + Inches(0.39)

    # ==========================================
    # SLIDE 3: Scopul & Obiectivele Proiectului
    # ==========================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_bg(slide3, dark=False)
    add_header(slide3, "Scopul Proiectului BacApp2-Qwen", "VIZIUNE & OBIECTIVE STRATEGICE")

    add_card(slide3, Inches(0.8), Inches(1.8), Inches(4.8), Inches(4.8), bg_color=C_CARD_DARK)
    tb_left = slide3.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(4.2), Inches(4.2))
    tf_l = tb_left.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Viziunea Centrală"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY_LIGHT
    p.space_after = Pt(14)

    p_v = tf_l.add_paragraph()
    p_v.text = "Transformarea pregătirii pentru examenul de Bacalaureat dintr-un proces mecanic într-o experiență interactivă, structurată și ancorată 100% factual prin fuzionarea Knowledge Graph-urilor literare cu modele LLM de ultimă generație (Qwen)."
    p_v.font.size = Pt(14)
    p_v.font.color.rgb = C_TEXT_LIGHT
    p_v.space_after = Pt(16)

    p_v2 = tf_l.add_paragraph()
    p_v2.text = "🎯 Zero halucinații factuale\n🎯 Generare automată de itemi pe 8 nivele\n🎯 Parcurs complet: Înțelegere ➔ Testare ➔ Eseu"
    p_v2.font.size = Pt(13)
    p_v2.font.color.rgb = C_ACCENT_GOLD

    right_objs = [
        ("1. Ancorare Factuală Strictă (Grounding)", "Eliminarea completă a erorilor literare prin modelarea operelor în Knowledge Graph-uri verificate primar.", C_PRIMARY),
        ("2. Generare Automată & Scalabilă de Conținut", "Construcția automată de exerciții multi-format (grile, flashcards, cronologii, asocieri) cu control determinist al costurilor.", C_ACCENT_BLUE),
        ("3. Asistență Metodologică la Redactare", "Ghidarea elevilor în formularea argumentelor, integrarea scenelor-cheie și respectarea cerințelor baremului oficial de BAC.", C_ACCENT_GREEN)
    ]
    top_pos = Inches(1.8)
    for o_title, o_desc, o_col in right_objs:
        c = add_card(slide3, Inches(5.9), top_pos, Inches(6.6), Inches(1.45))
        edge = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(5.9), top_pos, Inches(0.1), Inches(1.45))
        edge.fill.solid()
        edge.fill.fore_color.rgb = o_col
        edge.line.fill.background()

        tb = slide3.shapes.add_textbox(Inches(6.2), top_pos + Inches(0.15), Inches(6.1), Inches(1.15))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = o_title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK

        pd = tf.add_paragraph()
        pd.text = o_desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = C_TEXT_MUTED
        pd.space_before = Pt(4)

        top_pos += Inches(1.68)

    # ==========================================
    # SLIDE 4: Arhitectura Sistemului
    # ==========================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_bg(slide4, dark=False)
    add_header(slide4, "Arhitectura Tehnică End-to-End a Proiectului", "STRUCTURĂ ȘI FLUX DE DATE")

    arch_layers = [
        ("Nivelul de Date & Cunoștințe", "• Knowledge Graph (Ontologie: Evenimente, Personaje, Teme)\n• Sub-grafuri pe capitole\n• Dovezi primare PDF (citate, pagini)\n• Registre de metadate & works.py", C_PRIMARY),
        ("Nivelul de Procesare AI & Generare", "• Graph Packets deterministe\n• Qwen 3.7 / 3.5 Flash via OpenRouter\n• Reasoning Effort adaptiv (Medium/High)\n• Pipeline `testare_rapida.py`", C_ACCENT_BLUE),
        ("Nivelul de Validare & Evaluare", "• Validator local structural & lexical\n• Sentence-Transformers (MiniLM) deduplicare\n• Profiler stilistic & penalizări\n• Logging complet tokeni & costuri", C_ACCENT_GOLD),
        ("Nivelul UI & Experiență Elev", "• Streamlit Application (app.py)\n• 7 Componente Custom HTML/JS/CSS\n• Mindmaps interactive de eseu\n• Gamification (Progress Orbs)", C_ACCENT_GREEN)
    ]

    card_w = Inches(2.76)
    card_h = Inches(4.8)
    left_start = Inches(0.8)
    for i, (l_title, l_desc, l_col) in enumerate(arch_layers):
        pos_x = left_start + i * (card_w + Inches(0.23))
        add_card(slide4, pos_x, Inches(1.8), card_w, card_h)

        tag = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, pos_x, Inches(1.8), card_w, Inches(0.6))
        tag.fill.solid()
        tag.fill.fore_color.rgb = l_col
        tag.line.fill.background()

        tb_tag = slide4.shapes.add_textbox(pos_x + Inches(0.1), Inches(1.85), card_w - Inches(0.2), Inches(0.5))
        tf_tag = tb_tag.text_frame
        tf_tag.word_wrap = True
        pt = tf_tag.paragraphs[0]
        pt.text = f"NIVEL {i+1}"
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_LIGHT
        pt.alignment = PP_ALIGN.CENTER

        tb_c = slide4.shapes.add_textbox(pos_x + Inches(0.2), Inches(2.55), card_w - Inches(0.4), card_h - Inches(0.9))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        pt2 = tf_c.paragraphs[0]
        pt2.text = l_title
        pt2.font.size = Pt(14)
        pt2.font.bold = True
        pt2.font.color.rgb = C_TEXT_DARK
        pt2.space_after = Pt(10)

        pd = tf_c.add_paragraph()
        pd.text = l_desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = C_TEXT_MUTED

    # ==========================================
    # SLIDE 5: Ontologia și Knowledge Graph-ul Literar
    # ==========================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_bg(slide5, dark=False)
    add_header(slide5, "Modelarea Literară: Ontologia Knowledge Graph-ului", "FUNDAȚIA FACTUALĂ A CUNOAȘTERII")

    add_card(slide5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tb_ont_l = slide5.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
    tf_ol = tb_ont_l.text_frame
    tf_ol.word_wrap = True
    p = tf_ol.paragraphs[0]
    p.text = "Structura Grafului Canonic («Ion»)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p.space_after = Pt(10)

    p_stats = tf_ol.add_paragraph()
    p_stats.text = (
        "• 1 Operă (`Work`) & 1 Autor (`Author`)\n"
        "• 2 Părți («Glasul pământului», «Glasul iubirii»)\n"
        "• 13 Capitole narative complete (de la «Începutul» la «Sfârșitul»)\n"
        "• 124 Evenimente Narative (`NarrativeEvent`) ordonate global & local\n"
        "• 24 Personaje (`Character`) cu relații inter-umane reificate\n"
        "• 14 Locații (`Location`), 5 Conflicte majore, 9 Teme literare\n"
        "• 4 Valori morale/sociale, 26 Stări narative de capitol"
    )
    p_stats.font.size = Pt(12.5)
    p_stats.font.color.rgb = C_TEXT_DARK
    p_stats.space_after = Pt(12)

    p_exp = tf_ol.add_paragraph()
    p_exp.text = "📌 Fiecare eveniment include verbalizare simplă + elevată, dovezi primare (locator PDF / citat text) și participanți."
    p_exp.font.size = Pt(12)
    p_exp.font.color.rgb = C_PRIMARY

    add_card(slide5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    tb_ont_r = slide5.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.4))
    tf_or = tb_ont_r.text_frame
    tf_or.word_wrap = True
    pr = tf_or.paragraphs[0]
    pr.text = "Relații Controlate & Tipuri de Legături"
    pr.font.size = Pt(17)
    pr.font.bold = True
    pr.font.color.rgb = C_ACCENT_BLUE
    pr.space_after = Pt(10)

    pr_desc = tf_or.add_paragraph()
    pr_desc.text = (
        "1. Ierarhie Structurală:\n"
        "   part_of, has_chapter, occurs_in_chapter\n\n"
        "2. Dependențe Temporale & Secvențiale:\n"
        "   occurs_before, immediately_precedes, immediately_follows\n\n"
        "3. Relații Cauzale & Motivaționale:\n"
        "   causes, contributes_to, enables, results_in\n\n"
        "4. Participare & Dimensiune Critică:\n"
        "   involves_character, illustrates_theme, triggers_conflict\n\n"
        "🛡️ Rigurozitate: Evenimentele interpretative nesusținute sunt trecute în `excluded_events`."
    )
    pr_desc.font.size = Pt(12.5)
    pr_desc.font.color.rgb = C_TEXT_DARK

    # ==========================================
    # SLIDE 6: Structura Aplicației - Interfața Utilizator
    # ==========================================
    slide6 = prs.slides.add_slide(blank_layout)
    add_bg(slide6, dark=False)
    add_header(slide6, "Arhitectura Frontend: Streamlit & Componente Custom", "INTERFAȚA ȘI EXPERIENȚA UTILIZATORULUI")

    cards_ui = [
        ("Workspace pe 3 Taburi", "Fiecare operă literară oferă 3 moduri dedicate de studiu:\n1. «Înțelege opera»\n2. «Testare rapidă»\n3. «Construiește eseu»\nNavigare intuitivă și memorarea preferințelor de tab.", C_PRIMARY),
        ("7 Componente Custom Web", "Extensii Streamlit cu JavaScript, CSS și HTML izolate:\n• Chronology Drag & Drop\n• Flashcard Flip & Spaced Review\n• Matching Pairs & Word Fill\n• Mindmap Viewer & Scene Annotator", C_ACCENT_BLUE),
        ("Gamification & Progres", "• Progress Orbs interactive\n• Calcul procentual de stăpânire per operă\n• Salvare deterministă în progres local (`data/progress.py`)\n• Posibilitate de resetare și auditare", C_ACCENT_GREEN)
    ]

    c_w = Inches(3.64)
    c_h = Inches(4.8)
    x_pos = Inches(0.8)
    for u_title, u_desc, u_col in cards_ui:
        add_card(slide6, x_pos, Inches(1.8), c_w, c_h)
        b = slide6.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_pos, Inches(1.8), c_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = u_col
        b.line.fill.background()

        tb = slide6.shapes.add_textbox(x_pos + Inches(0.25), Inches(2.1), c_w - Inches(0.5), c_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = u_title
        pt.font.size = Pt(17)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = u_desc
        pd.font.size = Pt(13)
        pd.font.color.rgb = C_TEXT_MUTED
        x_pos += c_w + Inches(0.39)

    # ==========================================
    # SLIDE 7: Taburile Aplicației (Detaliere Moduri)
    # ==========================================
    slide7 = prs.slides.add_slide(blank_layout)
    add_bg(slide7, dark=False)
    add_header(slide7, "Cele 3 Piloni de Învățare din Aplicație", "FLUXUL COMPLET DE ASIMILARE AL OPEREI")

    modes = [
        ("Tab 1: Înțelege Opera", "Ghidaj Teoretic & Vizual", 
         "• Sinteza curentului literar & speciei\n• Rezumate validate pe toate cele 13 capitole\n• Scheme compoziționale (Titlu, Incipit-Final, Conflicte)\n• Hărți mentale ale personajelor & relațiilor\n• Adnotări pe scene-cheie", C_PRIMARY),
        ("Tab 2: Testare Rapidă", "Bancă Automată de Exerciții", 
         "• Grile cu variante multiple (MCQ)\n• Exerciții de ordonare cronologică interactivă\n• Exerciții de completare a lacunelor (Fill-in)\n• Flashcards cu repetiție spațiată\n• Asocieri (personaj-acțiune-statut)", C_ACCENT_BLUE),
        ("Tab 3: Construiește Eseu", "Asistență la Redactare Structurată", 
         "• Generare schemă eseu conform baremului BAC\n• Formulare ipoteză, argumente & scene demonstrative\n• Integrarea citatelor primare verificate\n• Mindmap interactiv al eseului\n• Evaluare & sugestii de îmbunătățire stilistică", C_ACCENT_GOLD)
    ]

    c_w = Inches(3.64)
    c_h = Inches(4.8)
    x_pos = Inches(0.8)
    for m_title, m_sub, m_desc, m_col in modes:
        add_card(slide7, x_pos, Inches(1.8), c_w, c_h)
        b = slide7.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_pos, Inches(1.8), c_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = m_col
        b.line.fill.background()

        tb = slide7.shapes.add_textbox(x_pos + Inches(0.25), Inches(2.1), c_w - Inches(0.5), c_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = m_title
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK

        ps = tf.add_paragraph()
        ps.text = m_sub
        ps.font.size = Pt(12)
        ps.font.bold = True
        ps.font.color.rgb = m_col
        ps.space_after = Pt(10)

        pd = tf.add_paragraph()
        pd.text = m_desc
        pd.font.size = Pt(12.5)
        pd.font.color.rgb = C_TEXT_MUTED
        x_pos += c_w + Inches(0.39)

    # ==========================================
    # SLIDE 8: Pipeline-ul de Generare Automată (testare_rapida.py)
    # ==========================================
    slide8 = prs.slides.add_slide(blank_layout)
    add_bg(slide8, dark=False)
    add_header(slide8, "Pipeline-ul de Generare Automată («testare_rapida.py»)", "AUTOMATIZARE ȘI SCALABILITATE")

    steps_pipe = [
        ("1. Input & Parsare Graf", "Primește fișierul `knowledge-graph.json`, extrage metadata, capitolele, nodurile și aserțiunile ontologice.", C_PRIMARY),
        ("2. Planificare Loturi (Batches)", "Generează 96 de întrebări (4 loturi x 24 întrebări). Exclude istoricul rezervat anterior pentru a evita repetițiile.", C_ACCENT_BLUE),
        ("3. Apeluri Qwen Dedicate", "Execută 32 de apeluri izolate către Qwen Flash (`reasoning=medium`). Fiecare apel acoperă o categorie specifică.", C_ACCENT_GOLD),
        ("4. Construcție Artefacte UI", "Generează automat fișierele consumate de UI: `questions.json`, `flashcards.json`, exerciții de cronologie, completare și asociere.", C_ACCENT_GREEN)
    ]

    top_p = Inches(1.8)
    for st_title, st_desc, st_col in steps_pipe:
        c = add_card(slide8, Inches(0.8), top_p, Inches(11.7), Inches(1.1))
        e = slide8.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), top_p, Inches(0.12), Inches(1.1))
        e.fill.solid()
        e.fill.fore_color.rgb = st_col
        e.line.fill.background()

        tb = slide8.shapes.add_textbox(Inches(1.2), top_p + Inches(0.15), Inches(11.1), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = st_title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK

        pd = tf.add_paragraph()
        pd.text = st_desc
        pd.font.size = Pt(12.5)
        pd.font.color.rgb = C_TEXT_MUTED
        pd.space_before = Pt(3)

        top_p += Inches(1.25)

    # ==========================================
    # SLIDE 9: Cercetarea - Privire de Ansamblu & Metodologie
    # ==========================================
    slide9 = prs.slides.add_slide(blank_layout)
    add_bg(slide9, dark=True)
    add_header(slide9, "Cadrul de Cercetare Științifică și Benchmark-urile Proiectului", "METODOLOGIE ȘI EVALUARE RIGUROASĂ", dark=True)

    c_exp_w = Inches(3.64)
    c_exp_h = Inches(4.8)
    x_exp = Inches(0.8)
    exp_data = [
        ("Experimentul 1: Benchmark & Tipologii", "Definirea celor 8 tipologii cognitive de întrebări (Low/Mid/High-Hop) și compararea primară a modelelor pe subgraful Capitolului I.", "• Evaluator determinist de JSON\n• Scoring pe acoperire de graf\n• Baseline: DeepSeek v4 Flash, Gemini 2.5 Flash Lite", C_PRIMARY_LIGHT),
        ("Experimentul 2: Semantică & Stil", "Introducerea Sentence-Transformers pentru eliminarea duplicatelor semantice și a unui profiler stilistic pentru rezumate.", "• Model: `paraphrase-multilingual-MiniLM`\n• Calibrare automată prag cosinus\n• Penalizări lexicale (expresii umplutură)", C_ACCENT_BLUE),
        ("Experimentul 3: RQUGE-Ro & Qwen", "Adaptarea RQUGE pentru limba română (mT5 + XLM-RoBERTa) și optimizarea familiei Qwen (3.7 / 3.5 Flash) pentru producție.", "• Factual Protection cu dovezi PDF\n• Reasoning effort adaptiv\n• Cost-efficiency: $0.01/set complet", C_ACCENT_GOLD)
    ]

    for e_t, e_sub, e_b, e_c in exp_data:
        add_card(slide9, x_exp, Inches(1.8), c_exp_w, c_exp_h, bg_color=C_CARD_DARK, border_color=RGBColor(51, 65, 85))
        b = slide9.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_exp, Inches(1.8), c_exp_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = e_c
        b.line.fill.background()

        tb = slide9.shapes.add_textbox(x_exp + Inches(0.25), Inches(2.1), c_exp_w - Inches(0.5), c_exp_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = e_t
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_LIGHT

        ps = tf.add_paragraph()
        ps.text = e_sub
        ps.font.size = Pt(12)
        ps.font.color.rgb = RGBColor(203, 213, 225)
        ps.space_before = Pt(6)
        ps.space_after = Pt(12)

        pb = tf.add_paragraph()
        pb.text = e_b
        pb.font.size = Pt(12.5)
        pb.font.color.rgb = e_c
        x_exp += c_exp_w + Inches(0.39)

    # ==========================================
    # SLIDE 10: Experimentul 1 - Cele 8 Tipologii de Întrebări
    # ==========================================
    slide10 = prs.slides.add_slide(blank_layout)
    add_bg(slide10, dark=False)
    add_header(slide10, "Experimentul 1: Cele 8 Tipologii Cognitive de Întrebări", "TAXONOMIA COMPLEXITĂȚII ÎNTREBĂRILOR")

    col1_items = [
        ("1. Simple Facts (Low-hop)", "Interogare directă a atributelor de bază (ex: autor, locație, obiect)."),
        ("2. Character Relations (Low-hop)", "Relații de rudenie, alianță, căsătorie sau dușmănie între personaje."),
        ("3. Narrative Actions (Low-hop)", "Acțiuni concrete desfășurate de personaje într-o scenă specifică."),
        ("4. Temporal Order (Mid-hop)", "Ordonarea corectă a 3-4 evenimente consecutive dintr-un capitol.")
    ]
    col2_items = [
        ("5. Cause & Effect (Mid-hop)", "Identificarea motivațiilor interne și a consecințelor directe ale unei alegeri."),
        ("6. Character Evolution (High-hop)", "Transformarea psihologică sau de statut a personajului de-a lungul capitolelor."),
        ("7. Literary Interpretation (High-hop)", "Corelarea evenimentelor cu teme majore, conflicte și simboluri literare."),
        ("8. Cross-Chapter Comparison (High-hop)", "Comparații de structură, comportament sau motive între capitole diferite.")
    ]

    for col_idx, items in enumerate([col1_items, col2_items]):
        left_c = Inches(0.8) if col_idx == 0 else Inches(6.8)
        top_c = Inches(1.8)
        for t_title, t_desc in items:
            c = add_card(slide10, left_c, top_c, Inches(5.7), Inches(1.1))
            bar_c = slide10.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_c, top_c, Inches(0.1), Inches(1.1))
            bar_c.fill.solid()
            bar_c.fill.fore_color.rgb = C_PRIMARY if col_idx == 0 else C_ACCENT_BLUE
            bar_c.line.fill.background()

            tb = slide10.shapes.add_textbox(left_c + Inches(0.25), top_c + Inches(0.12), Inches(5.3), Inches(0.85))
            tf = tb.text_frame
            tf.word_wrap = True
            pt = tf.paragraphs[0]
            pt.text = t_title
            pt.font.size = Pt(14)
            pt.font.bold = True
            pt.font.color.rgb = C_TEXT_DARK

            pd = tf.add_paragraph()
            pd.text = t_desc
            pd.font.size = Pt(11.5)
            pd.font.color.rgb = C_TEXT_MUTED
            pd.space_before = Pt(2)
            top_c += Inches(1.25)

    # ==========================================
    # SLIDE 11: Experimentul 2 - Similaritate Semantică & Profil Stilistic
    # ==========================================
    slide11 = prs.slides.add_slide(blank_layout)
    add_bg(slide11, dark=False)
    add_header(slide11, "Experimentul 2: Similaritate Semantică & Control Stilistic", "ELIMINAREA DUPLICATELOR ȘI REGLAJUL LEXICAL")

    add_card(slide11, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tb_s11_l = slide11.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
    tf_11l = tb_s11_l.text_frame
    tf_11l.word_wrap = True
    p = tf_11l.paragraphs[0]
    p.text = "1. Deduplicare Semantică cu MiniLM"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p.space_after = Pt(10)

    p_11l = tf_11l.add_paragraph()
    p_11l.text = (
        "• Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`\n\n"
        "• Transformă întrebările în embeddinguri normalizate și calculează similaritatea cosinus.\n\n"
        "• Scriptul `calibrate_similarity.py` calibrează pragurile de duplicare pe perechi etichetate (ex: 0.74 - 0.82).\n\n"
        "• Rezultat: Previne generarea a două întrebări cu același sens formulate cu cuvinte diferite."
    )
    p_11l.font.size = Pt(12.5)
    p_11l.font.color.rgb = C_TEXT_DARK

    add_card(slide11, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    tb_s11_r = slide11.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.4))
    tf_11r = tb_s11_r.text_frame
    tf_11r.word_wrap = True
    p2 = tf_11r.paragraphs[0]
    p2.text = "2. Profiler Stilistic Automat (`text_profile.py`)"
    p2.font.size = Pt(17)
    p2.font.bold = True
    p2.font.color.rgb = C_ACCENT_BLUE
    p2.space_after = Pt(10)

    p_11r = tf_11r.add_paragraph()
    p_11r.text = (
        "• Evaluatorul măsoară automat parametrii stilistici ai rezumatelor generate:\n"
        "   - Raportul conectorilor discursivi\n"
        "   - Rata expresiilor de umplutură (filler words)\n"
        "   - Lungimea medie a propozițiilor\n"
        "   - Ponderea numelor de personaje din graf\n"
        "   - Repetarea excesivă a aceluiași conector\n\n"
        "• Penalizare automată: Până la -10 puncte dacă rezumatul nu respectă profilul de referință."
    )
    p_11r.font.size = Pt(12.5)
    p_11r.font.color.rgb = C_TEXT_DARK

    # ==========================================
    # SLIDE 12: Experimentul 3 & Cercetarea RQUGE-Ro
    # ==========================================
    slide12 = prs.slides.add_slide(blank_layout)
    add_bg(slide12, dark=False)
    add_header(slide12, "Experimentul 3: Framework-ul RQUGE Adaptat pentru Română", "EVALUAREA CALITĂȚII ÎNTREBĂRILOR FĂRĂ EVALUATORI UMANI")

    rquge_cards = [
        ("Arhitectura în 2 Etape (RQUGE)", "Adaptare după lucrarea științifică RQUGE:\n1. Extragerea span-urilor candidate de răspuns din text.\n2. Generarea și scorarea întrebărilor corespondente pe baza referințelor din graf.", C_PRIMARY),
        ("Modele & Fine-Tuning în Română", "Înlocuirea modelelor mari în engleză cu arhitecturi eficiente multilingve:\n• `google/mt5-small` (generare)\n• `FacebookAI/xlm-roberta-base` (scorare)\n• Suport LoRA și fine-tuning pe XQuAD-ro & SQuAD.", C_ACCENT_BLUE),
        ("Obiectiv & Validare", "• Evaluare automată a relevanței, clarității și adecvării pedagogice a întrebărilor.\n• Calculul corelației Pearson/Spearman cu notele acordate de profesori umani pe seturi de testare dedicate.", C_ACCENT_GREEN)
    ]

    x_rq = Inches(0.8)
    for rq_t, rq_d, rq_c in rquge_cards:
        add_card(slide12, x_rq, Inches(1.8), c_w, c_h)
        b = slide12.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_rq, Inches(1.8), c_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = rq_c
        b.line.fill.background()

        tb = slide12.shapes.add_textbox(x_rq + Inches(0.25), Inches(2.1), c_w - Inches(0.5), c_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = rq_t
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = rq_d
        pd.font.size = Pt(13)
        pd.font.color.rgb = C_TEXT_MUTED
        x_rq += c_w + Inches(0.39)

    # ==========================================
    # SLIDE 13: Optimizarea & Integrarea Modelului Qwen
    # ==========================================
    slide13 = prs.slides.add_slide(blank_layout)
    add_bg(slide13, dark=False)
    add_header(slide13, "Integrarea Modelului Qwen («cercetare-qwen»)", "PERFORMANȚĂ, REASONING ȘI CONTROLUL COSTURILOR")

    grid_items = [
        ("Modelul Qwen 3.7 Flash & 3.5 Flash", "Alegerea familiei Qwen oferă un echilibru remarcabil între capabilități lingvistice superioare în limba română, viteză de execuție și costuri reduse per apel.", C_PRIMARY),
        ("Controlul Parametrilor de Reasoning", "Folosirea reasoning-ului `medium` pentru rezolvarea conexiunilor cauzale și a evoluției personajelor, obținând raționamente literare complexe fără degradare de viteză.", C_ACCENT_BLUE),
        ("Execuție Modulară pe 24 Sarcini", "Runner secvențial determinist: 8 categorii de întrebări + 13 rezumate de capitole + 3 elemente compoziționale (Titlu, Incipit-Final, Conflict).", C_ACCENT_GOLD),
        ("Persistență & Reziliență la Reluare", "Sistem complet de checkpointing (`--resume-run`). Sarcinile validate nu sunt reapelate, iar consumul de tokeni este urmărit cu precizie de audit.", C_ACCENT_GREEN)
    ]

    for idx, (g_t, g_d, g_c) in enumerate(grid_items):
        row = idx // 2
        col = idx % 2
        gx = Inches(0.8) if col == 0 else Inches(6.8)
        gy = Inches(1.8) if row == 0 else Inches(4.3)

        add_card(slide13, gx, gy, Inches(5.7), Inches(2.3))
        b = slide13.shapes.add_shape(MSO_SHAPE.RECTANGLE, gx, gy, Inches(0.1), Inches(2.3))
        b.fill.solid()
        b.fill.fore_color.rgb = g_c
        b.line.fill.background()

        tb = slide13.shapes.add_textbox(gx + Inches(0.25), gy + Inches(0.2), Inches(5.3), Inches(1.9))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = g_t
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK

        pd = tf.add_paragraph()
        pd.text = g_d
        pd.font.size = Pt(12)
        pd.font.color.rgb = C_TEXT_MUTED
        pd.space_before = Pt(6)

    # ==========================================
    # SLIDE 14: Protecția Factuală & Eliminarea Halucinațiilor
    # ==========================================
    slide14 = prs.slides.add_slide(blank_layout)
    add_bg(slide14, dark=True)
    add_header(slide14, "Mecanisme Avansate de Protecție Factuală", "CUM GARANTĂM ZERO HALUCINAȚII LITERARE", dark=True)

    sec_cards = [
        ("Pachete cu Dovezi Primare Verificate", "Fiecare pachet trimis modelului include doar evenimente marcate `verified_primary`, însoțite de locatorul paginii din PDF și de citatul exact din roman.", C_PRIMARY_LIGHT),
        ("Lista de Evenimente Excluse", "Evenimentele insuficient documentate sau pur speculative sunt izolate în `excluded_events`. Promptul interzice explicit verbalizarea acestora.", C_ACCENT_BLUE),
        ("Validator Lexical & Factual Strict", "Verifică alinierea lexicală directă între propozițiile generate și citatele primare. Respinge automat exagerările nefondate («definitiv», «instantaneu», «exclusiv»).", C_ACCENT_GOLD)
    ]

    x_sec = Inches(0.8)
    for s_t, s_d, s_c in sec_cards:
        add_card(slide14, x_sec, Inches(1.8), c_w, c_h, bg_color=C_CARD_DARK, border_color=RGBColor(51, 65, 85))
        b = slide14.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_sec, Inches(1.8), c_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = s_c
        b.line.fill.background()

        tb = slide14.shapes.add_textbox(x_sec + Inches(0.25), Inches(2.1), c_w - Inches(0.5), c_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = s_t
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_LIGHT
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = s_d
        pd.font.size = Pt(13)
        pd.font.color.rgb = RGBColor(203, 213, 225)
        x_sec += c_w + Inches(0.39)

    # ==========================================
    # SLIDE 15: Analiza Costurilor & Eficienței
    # ==========================================
    slide15 = prs.slides.add_slide(blank_layout)
    add_bg(slide15, dark=False)
    add_header(slide15, "Eficiența Resurselor: Token Usage și Analiza Costurilor", "SUSTENABILITATE ȘI OPTIMIZARE ECONOMICĂ")

    add_card(slide15, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tb_c_l = slide15.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
    tf_cl = tb_c_l.text_frame
    tf_cl.word_wrap = True
    p = tf_cl.paragraphs[0]
    p.text = "Metrici de Cost (Rulare Completă Qwen)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p.space_after = Pt(10)

    p_c_stats = tf_cl.add_paragraph()
    p_c_stats.text = (
        "• Cost per set de 24 întrebări: ~ $0.010 - $0.034 USD\n\n"
        "• Cost per rezumat de capitol: < $0.003 USD\n\n"
        "• Cost total generare conținut complet per operă (96 întrebări + 13 rezumate + 3 scheme): sub $0.10 USD\n\n"
        "• Eficiență extraordinară comparativ cu GPT-4 / Claude 3.5 Sonnet (reducere de peste 95% a costurilor API)."
    )
    p_c_stats.font.size = Pt(13)
    p_c_stats.font.color.rgb = C_TEXT_DARK

    add_card(slide15, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    tb_c_r = slide15.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.4))
    tf_cr = tb_c_r.text_frame
    tf_cr.word_wrap = True
    p2 = tf_cr.paragraphs[0]
    p2.text = "Sistemul de Auditare & Gestiune Tokeni"
    p2.font.size = Pt(17)
    p2.font.bold = True
    p2.font.color.rgb = C_ACCENT_BLUE
    p2.space_after = Pt(10)

    p_cr = tf_cr.add_paragraph()
    p_cr.text = (
        "• `token-usage.csv` consemnează fiecare apel (prompt, completion, reasoning tokens).\n\n"
        "• `raport-rulare.md` și `raport-cost-intrebari.md` sunt generate automat fără costuri AI adiționale.\n\n"
        "• `manifest.json` îngheață hash-urile prompturilor și subgrafurilor utilizate pentru reproductibilitate 100%.\n\n"
        "• Niciun token nu se pierde la reluarea unei sesiuni întrerupte."
    )
    p_cr.font.size = Pt(13)
    p_cr.font.color.rgb = C_TEXT_DARK

    # ==========================================
    # SLIDE 16: Stack-ul Tehnologic Complet
    # ==========================================
    slide16 = prs.slides.add_slide(blank_layout)
    add_bg(slide16, dark=False)
    add_header(slide16, "Stack-ul Tehnologic Integrat", "TEHNOLOGII, FRAMEWORK-URI ȘI MODELE")

    tech_categories = [
        ("Core & Backend", "• Python 3.12 / 3.13\n• Virtual environments\n• JSON Schemas & Validators\n• Unittest Suite automat", C_PRIMARY),
        ("Interfață & Componente", "• Streamlit (Multi-page & Tabs)\n• HTML5 / CSS3 (Glassmorphism)\n• Custom JS Component Extensions\n• Session State Management", C_ACCENT_BLUE),
        ("Modele AI & LLM", "• Qwen 3.7 / 3.5 Flash (OpenRouter)\n• DeepSeek v4 Flash, Gemini 2.5\n• Sentence-Transformers (MiniLM)\n• mT5-small & XLM-RoBERTa", C_ACCENT_GOLD),
        ("Date & Knowledge Graph", "• Ontologie literară dedicată\n• JSON Graph Databases\n• RAG & Indexare Citate Primare\n• Reprezentări grafice & Mindmaps", C_ACCENT_GREEN)
    ]

    for i, (t_title, t_desc, t_col) in enumerate(tech_categories):
        pos_x = left_start + i * (card_w + Inches(0.23))
        add_card(slide16, pos_x, Inches(1.8), card_w, card_h)

        b = slide16.shapes.add_shape(MSO_SHAPE.RECTANGLE, pos_x, Inches(1.8), card_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = t_col
        b.line.fill.background()

        tb = slide16.shapes.add_textbox(pos_x + Inches(0.2), Inches(2.1), card_w - Inches(0.4), card_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = t_title
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_DARK
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = t_desc
        pd.font.size = Pt(12.5)
        pd.font.color.rgb = C_TEXT_MUTED

    # ==========================================
    # SLIDE 17: Concluzii, Impact & Direcții Viitoare
    # ==========================================
    slide17 = prs.slides.add_slide(blank_layout)
    add_bg(slide17, dark=True)
    add_header(slide17, "Concluzii, Impact Educațional și Direcții Viitoare", "REZUMAT EXECUTIV ȘI DEZVOLTĂRI ULTERIOARE", dark=True)

    c_c_w = Inches(3.64)
    c_c_h = Inches(4.8)
    x_c = Inches(0.8)
    conc_data = [
        ("Ce S-a Realizat cu Succes", "• Arhitectură hibridă funcțională (KG + Qwen + Streamlit).\n• Generare automată de conținut cu zero halucinații factuale.\n• Bază științifică solidă (3 experimente & benchmarking riguros).\n• Eficiență extremă de cost.", C_PRIMARY_LIGHT),
        ("Impactul Asupra Elevilor", "• Înțelegere structurală profundă în locul tocirii mecanice.\n• Feedback instantaneu și învățare activă adaptivă.\n• Dezvoltarea abilităților de analiză critică și eseu argumentativ conform cerințelor de examen.", C_ACCENT_GREEN),
        ("Evoluție & Direcții Viitoare", "• Extinderea ontologiei la toate cele 14+ opere canonice din programa de BAC.\n• Activarea evaluării automate RQUGE-Ro antrenată pe dataseturi românești.\n• Lansarea ca platformă web publică scalabilă.", C_ACCENT_GOLD)
    ]

    for c_t, c_d, c_col in conc_data:
        add_card(slide17, x_c, Inches(1.8), c_c_w, c_c_h, bg_color=C_CARD_DARK, border_color=RGBColor(51, 65, 85))
        b = slide17.shapes.add_shape(MSO_SHAPE.RECTANGLE, x_c, Inches(1.8), c_c_w, Inches(0.12))
        b.fill.solid()
        b.fill.fore_color.rgb = c_col
        b.line.fill.background()

        tb = slide17.shapes.add_textbox(x_c + Inches(0.25), Inches(2.1), c_c_w - Inches(0.5), c_c_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = c_t
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_LIGHT
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = c_d
        pd.font.size = Pt(13)
        pd.font.color.rgb = RGBColor(203, 213, 225)
        x_c += c_c_w + Inches(0.39)

    out_path = os.path.abspath("Prezentare_BacApp2_Qwen.pptx")
    prs.save(out_path)
    print(f"Presentation saved successfully to: {out_path}")

if __name__ == "__main__":
    create_deck()
