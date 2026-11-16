"""Build the student TD handout OWASP-JuiceLab-TD-Eleves.docx.

Clearer than the book appendix: one structured sheet per challenge (goal,
notion, numbered steps with literal strings, how Juice Shop validates, why
it is a flaw, the fix, troubleshooting, a capture). Content comes from the
content_*.py modules; captures from docs/img/td-eleves/. Run from this
directory:  python3 build_guide_td.py
"""
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

import content_outro as OUTRO
from content_defense import DEFENSE
from content_intro import INTRO, PREP, READING, RULES, SCORE_BOARD
from content_dj1 import DJ1
from content_dj23 import DJ23

DOCS = Path('/home/fpizzi/workspace/juice/docs')
IMG = DOCS / 'img' / 'td-eleves'
OUT = DOCS / 'OWASP-JuiceLab-TD-Eleves.docx'
EXERCISES = DJ1 + DJ23

NAVY = '153E45'
TEAL = '11655B'
AMBER = '8A5A00'
GREY = '455761'
LIGHT = 'EAF4F2'
CODE_BG = 'F3F1EC'
DAY_THEMES = {
    1: 'Reconnaissance et exposition',
    2: 'Authentification et contrôle des accès',
    3: 'Injections dans le navigateur et usurpation d’identité',
}


def element(tag, **attrs):
    node = OxmlElement('w:' + tag)
    for key, value in attrs.items():
        node.set(qn('w:' + key), str(value))
    return node


def new_document():
    """A4 document with the JuiceLab styles and a page-number footer."""
    doc = Document()
    doc.core_properties.title = 'Travaux dirigés OWASP Juice Shop — guide élève'
    doc.core_properties.subject = 'Formation OWASP Juice Shop et parcours JuiceLab'
    doc.core_properties.author = 'JuiceLab'
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(1.85), Cm(1.6)
    section.left_margin = section.right_margin = Cm(2.05)
    section.footer_distance = Cm(0.75)
    for name, size, color in [
        ('Normal', 11, '17242B'), ('Title', 30, '000000'),
        ('Heading 1', 23, NAVY), ('Heading 2', 15, NAVY),
        ('Heading 3', 12, TEAL), ('Caption', 9, GREY),
    ]:
        style = doc.styles[name]
        style.font.name = 'Carlito'
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.italic = False
        style.paragraph_format.space_after = Pt(6)
        if name.startswith('Heading'):
            style.paragraph_format.space_before = Pt(10)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.13
    for bar in doc.styles['Title']._element.xpath('./w:pPr/w:pBdr'):
        bar.getparent().remove(bar)
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    run = footer.add_run('JuiceLab  ·  Support élève  ·  ')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string(GREY)
    footer._p.append(element('fldSimple', instr='PAGE'))
    return doc


def tag_line(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor.from_string(TEAL)
    return p


def label(doc, name, text, color=NAVY):
    """A bold lead-in label followed by body text, in one paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(name + '  ')
    run.bold = True
    run.font.color.rgb = RGBColor.from_string(color)
    p.add_run(text)
    return p


def code_run(paragraph, text):
    """Append a monospaced, shaded literal run (URL, payload, field name)."""
    run = paragraph.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor.from_string('1A1A1A')
    rpr = run._r.get_or_add_rPr()
    rpr.append(element('shd', val='clear', fill=CODE_BG))
    return run


def code_block(doc, text):
    """A standalone shaded code paragraph, one line per physical line."""
    for line in text.split('\n'):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        code_run(p, line)
    return p


def step(doc, number, text, code=None):
    """One manually numbered step so numbering restarts on every sheet."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.75)
    run = p.add_run(f'{number}.  ')
    run.bold = True
    run.font.color.rgb = RGBColor.from_string(NAVY)
    p.add_run(text)
    if code is not None:
        return code_block(doc, code)
    return p


def bullet(doc, text):
    return doc.add_paragraph(text, style='List Bullet')


def picture(doc, name, caption, width_cm=14.5, max_h_cm=9.5):
    path = IMG / (name + '.png')
    if not path.exists():
        return None
    with Image.open(path) as img:
        width_cm = min(width_cm, max_h_cm * img.width / img.height)
    p = doc.add_paragraph()
    p.alignment = 1
    p.paragraph_format.keep_with_next = True
    shape = p.add_run().add_picture(str(path), width=Cm(width_cm))
    shape._inline.docPr.set('descr', caption)
    cap = doc.add_paragraph(caption, 'Caption')
    cap.alignment = 1
    return p


def stars(n):
    return '★' * n + '☆' * (3 - n)


def page_break_heading(doc, text, level=1):
    p = doc.add_heading(text, level)
    p.paragraph_format.page_break_before = True
    return p


def build_front_matter(doc):
    tag_line(doc, 'FORMATION OWASP  /  SUPPORT ÉLÈVE')
    doc.add_paragraph('Travaux dirigés OWASP Juice Shop', 'Title')
    doc.add_paragraph(INTRO)
    label(doc, 'Cadre', RULES, AMBER)

    doc.add_heading('Préparer ta séance', 1)
    for line in PREP:
        bullet(doc, line)

    doc.add_heading('Comment lire une fiche', 2)
    for name, body in READING:
        p = doc.add_paragraph(style='List Bullet')
        run = p.add_run(name + ' : ')
        run.bold = True
        p.add_run(body)

    doc.add_heading(SCORE_BOARD['title'], 1)
    doc.add_paragraph(SCORE_BOARD['intro'])
    doc.add_heading('Ce que montre une carte', 3)
    for lm in SCORE_BOARD['landmarks']:
        bullet(doc, lm)
    for title, body in SCORE_BOARD['paras']:
        doc.add_heading(title, 3)
        doc.add_paragraph(body)
    cap = SCORE_BOARD.get('capture')
    if cap:
        picture(doc, cap[0], cap[1])

    doc.add_heading('Le cycle de travail d’un défi', 1)
    doc.add_paragraph(
        'Pour chaque défi, ouvre le coach avec le bouton TD, puis suis quatre '
        'onglets. Briefing : la mission et ce qu’il faut observer. Hints : des '
        'indices gradués, révélés un par un, dont le coût se cumule. '
        'After - logbook : ton journal (une observation, sa preuve, une '
        'protection ; vise au moins 50 mots). Quiz : trois questions de '
        'compréhension, avec un bouton Submit quiz en bas de la fenêtre.')
    picture(doc, 'e-td',
            'La carte du Score Board : le bouton TD ouvre le coach du défi.',
            10.5)


def build_sheet(doc, index, entry):
    i = index + 1
    day = entry['day']
    page_break_heading(doc, f'{i:02d}  {entry["title"]}', 1)
    meta = doc.add_paragraph()
    r = meta.add_run(f'Demi-journée {day} · {entry["category"]} · difficulté {stars(entry["difficulty"])}')
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(GREY)

    label(doc, 'But', entry['goal'])
    label(doc, 'À retenir', entry['notion'], TEAL)
    label(doc, 'Ta mission', entry['task'])
    label(doc, 'Question du journal', entry['question'], AMBER)

    doc.add_heading('Étapes', 2)
    for n, s in enumerate(entry['steps'], 1):
        if isinstance(s, tuple):
            step(doc, n, s[0], s[1])
        else:
            step(doc, n, s)

    doc.add_heading('Comment Juice Shop valide', 2)
    doc.add_paragraph(entry['validation'])

    doc.add_heading('Pourquoi c’est une faille', 2)
    doc.add_paragraph(entry['why'])

    doc.add_heading('La correction', 2)
    doc.add_paragraph(entry['fix'])

    defense = DEFENSE[entry['key']]
    doc.add_heading('Côté défense', 2)
    label(doc, 'Détecter', defense['detect'], TEAL)
    label(doc, 'Vérifier le correctif', defense['verify'], TEAL)

    if entry.get('trouble'):
        doc.add_heading('Si ça bloque', 2)
        for symptom, remedy in entry['trouble']:
            p = doc.add_paragraph(style='List Bullet')
            run = p.add_run(symptom + ' : ')
            run.bold = True
            p.add_run(remedy)

    label(doc, 'Pour aller plus loin', entry['further'], AMBER)

    picture(doc, f'p{i:02d}',
            f'Carte {entry["title"]} résolue : liseré et point verts.', 11.0, 6.0)
    if entry.get('book'):
        cap = doc.add_paragraph(
            f'Solution de référence : « Pwning OWASP Juice Shop », annexe '
            f'Challenge solutions, p. {entry["book"]}.', 'Caption')
        cap.paragraph_format.space_before = Pt(2)


def shade(cell, fill):
    cell._tc.get_or_add_tcPr().append(element('shd', val='clear', fill=fill))


def table(doc, header, rows, widths_cm):
    """Compact table with a navy header row and alternating row shading."""
    tab = doc.add_table(rows=1, cols=len(header))
    tab.style = 'Table Grid'
    tab.autofit = False
    for col, width in zip(tab.columns, widths_cm):
        col.width = Cm(width)
    for cell, text in zip(tab.rows[0].cells, header):
        shade(cell, NAVY)
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor.from_string('FFFFFF')
    tab.rows[0]._tr.get_or_add_trPr().append(element('tblHeader'))
    for n, row in enumerate(rows):
        cells = tab.add_row().cells
        for cell, text, width in zip(cells, row, widths_cm):
            cell.width = Cm(width)
            if n % 2 == 0:
                shade(cell, LIGHT)
            run = cell.paragraphs[0].add_run(text)
            run.font.size = Pt(10)
    return tab


def build_outro(doc):
    page_break_heading(doc, OUTRO.REFLEXES_TITLE, 1)
    doc.add_paragraph(OUTRO.REFLEXES_INTRO)
    for n, (head, body) in enumerate(OUTRO.REFLEXES, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.75)
        run = p.add_run(f'{n}.  {head}  ')
        run.bold = True
        run.font.color.rgb = RGBColor.from_string(NAVY)
        p.add_run(body)

    doc.add_heading('Récapitulatif des treize défis', 2)
    table(doc, ('N°', 'Défi', 'Famille', 'Contrôle clé'), OUTRO.RECAP,
          (1.1, 4.2, 5.0, 6.6))

    doc.add_heading(OUTRO.DELIVERABLE_TITLE, 2)
    for line in OUTRO.DELIVERABLE:
        bullet(doc, line)

    page_break_heading(doc, OUTRO.ASSESS_TITLE, 1)
    doc.add_paragraph(OUTRO.ASSESS_INTRO)
    doc.add_heading('Cinq questions, à chaque passage', 3)
    for n, q in enumerate(OUTRO.QUESTIONS, 1):
        step(doc, n, q)
    for title, body in (OUTRO.BEFORE, OUTRO.AFTER):
        doc.add_heading(title, 2)
        doc.add_paragraph(body)

    doc.add_heading(OUTRO.GRID_TITLE, 2)
    table(doc, ('Dimension', '0 point', '1 point', '2 points'), OUTRO.GRID,
          (3.6, 3.9, 4.4, 5.0))
    doc.add_paragraph(OUTRO.GRID_NOTE, 'Caption')


def main():
    doc = new_document()
    build_front_matter(doc)
    current_day = 0
    for index, entry in enumerate(EXERCISES):
        if entry['day'] != current_day:
            current_day = entry['day']
            page_break_heading(
                doc, f'Demi-journée {current_day}  ·  {DAY_THEMES[current_day]}', 1)
            doc.add_paragraph(
                'Ouvre chaque défi depuis le Score Board, travaille avec le '
                'coach, puis consigne ton journal et réponds au quiz.')
        build_sheet(doc, index, entry)
    build_outro(doc)
    assert len(EXERCISES) == 13, len(EXERCISES)
    assert set(DEFENSE) == {e['key'] for e in EXERCISES}
    # python-docx writes <w:zoom> without the schema-required percent.
    zoom = doc.settings.element.find(qn('w:zoom'))
    if zoom is not None:
        zoom.set(qn('w:percent'), '100')
    doc.save(str(OUT))
    print(f'written {OUT} ({OUT.stat().st_size} bytes, {len(EXERCISES)} sheets)')


if __name__ == '__main__':
    main()
