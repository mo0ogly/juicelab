"""Build the teacher handout OWASP-JuiceLab-Recette-Prof.docx.

Same sheets as the student guide plus teacher material: room setup, session
flow, expected answers, frequent mistakes, oral follow-ups, answer key of
the self-assessment and the recette report. Run from this directory:
    python3 build_guide_prof.py
"""
import json
from pathlib import Path

from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import content_outro as OUTRO
import content_prof as PROF
from build_guide_td import (
    AMBER, DAY_THEMES, DEFENSE, DOCS, EXERCISES, GREY, NAVY, TEAL,
    label, page_break_heading, picture, step, stars, table, tag_line,
    new_document,
)

OUT = DOCS / 'OWASP-JuiceLab-Recette-Prof.docx'
RECETTE = Path(__file__).parent / 'recette'


def solved(path):
    data = json.loads(path.read_text())
    return {k: bool(v['after'] and not v['before']) for k, v in data.items()}


def build_front(doc, before, after):
    tag_line(doc, 'FORMATION OWASP  /  SUPPORT PROFESSEUR')
    doc.add_paragraph('Corrigé et recette du TD OWASP Juice Shop', 'Title')
    doc.add_paragraph(PROF.INTRO)

    doc.add_heading('Préparer la salle', 1)
    for name, body in PROF.PREP_TECH:
        label(doc, name, body)

    doc.add_heading('Déroulé du TD', 1)
    doc.add_paragraph(PROF.FLOW_INTRO)
    table(doc, ('Demi-journée', 'Défis', 'Objectif'), PROF.FLOW, (2.6, 2.2, 12.1))
    doc.add_heading('Rythme d’une séance', 3)
    for n, line in enumerate(PROF.FLOW_STEPS, 1):
        step(doc, n, line)

    doc.add_heading('État des treize défis', 1)
    rows = []
    for i, e in enumerate(EXERCISES, 1):
        rows.append((f'{i:02d}', e['title'], f'{e["day"]}',
                     'Validé' if before.get(e['key']) else 'Non validé',
                     'Validé' if after.get(e['key']) else 'Non validé'))
    table(doc, ('N°', 'Défi', 'DJ', 'Docker avant correctif', 'Docker après correctif'),
          rows, (1.1, 5.0, 1.1, 4.8, 4.9))
    n_before, n_after = sum(before.values()), sum(after.values())
    doc.add_paragraph(
        f'Image Docker JuiceLab, OWASP Juice Shop 20.4.0-SNAPSHOT, instance '
        f'vierge : {n_before}/13 avant correctif (14 novembre 2026), {n_after}/13 '
        f'après (16 novembre 2026). Détail dans le procès-verbal en fin de '
        f'document.', 'Caption')


def build_sheet(doc, index, entry):
    i = index + 1
    page_break_heading(doc, f'{i:02d}  {entry["title"]}', 1)
    meta = doc.add_paragraph()
    r = meta.add_run(f'Demi-journée {entry["day"]} · {entry["category"]} · '
                     f'difficulté {stars(entry["difficulty"])}')
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(GREY)
    label(doc, 'Notion', entry['notion'], TEAL)
    label(doc, 'Mission donnée', entry['task'])

    note = PROF.TEACHER[entry['key']]
    doc.add_heading('Pour l’enseignant', 2)
    label(doc, 'Attendus', note['expected'], NAVY)
    label(doc, 'Erreurs fréquentes', note['pitfalls'], AMBER)
    label(doc, 'Relance orale', note['relance'], TEAL)

    doc.add_heading('Solution', 2)
    for n, s in enumerate(entry['steps'], 1):
        if isinstance(s, tuple):
            step(doc, n, s[0], s[1])
        else:
            step(doc, n, s)
    label(doc, 'Validation', entry['validation'])
    label(doc, 'Cause', entry['why'])
    label(doc, 'Correction', entry['fix'])
    defense = DEFENSE[entry['key']]
    label(doc, 'Détection', defense['detect'], TEAL)
    label(doc, 'Vérification', defense['verify'], TEAL)

    picture(doc, f'p{i:02d}', f'Carte {entry["title"]} résolue pendant la recette.',
            10.0, 5.5)
    if entry.get('book'):
        doc.add_paragraph(f'Référence : « Pwning OWASP Juice Shop », p. {entry["book"]}.',
                          'Caption')


def build_key(doc):
    page_break_heading(doc, 'Corrigé de l’auto-évaluation', 1)
    doc.add_paragraph(
        'Réponses attendues, à adapter : une réponse argumentée différente '
        'peut mériter les points. Le sujet complet figure dans le support élève.')
    for title, answers in (('Scénario « avant » : réservations', PROF.KEY_BEFORE),
                           ('Scénario « après » : suivi médical', PROF.KEY_AFTER)):
        doc.add_heading(title, 2)
        for n, (question, answer) in enumerate(zip(OUTRO.QUESTIONS, answers), 1):
            p = doc.add_paragraph()
            run = p.add_run(f'{n}.  {question}')
            run.bold = True
            run.font.color.rgb = RGBColor.from_string(NAVY)
            doc.add_paragraph(answer).paragraph_format.left_indent = Cm(0.75)
    doc.add_heading('Grille sur 8 points', 2)
    table(doc, ('Dimension', '0 point', '1 point', '2 points'), OUTRO.GRID,
          (3.6, 3.9, 4.4, 5.0))
    doc.add_paragraph(OUTRO.GRID_NOTE, 'Caption')


def build_recette(doc):
    page_break_heading(doc, 'Procès-verbal de recette', 1)
    doc.add_paragraph(PROF.RECETTE_INTRO)
    label(doc, 'Protocole', PROF.RECETTE_PROTOCOL)
    doc.add_heading('Écarts et décisions', 2)
    for name, body in PROF.RECETTE_FINDINGS:
        label(doc, name, body)
    doc.add_heading('Sources', 2)
    doc.add_paragraph(PROF.RECETTE_SOURCES)


def main():
    before = solved(RECETTE / 'results13-docker-avant-correctif.json')
    after = solved(RECETTE / 'results13-docker-apres-correctif.json')
    assert set(PROF.TEACHER) == {e['key'] for e in EXERCISES}
    doc = new_document('Corrigé et recette du TD OWASP Juice Shop', 'Support professeur')
    build_front(doc, before, after)
    day = 0
    for index, entry in enumerate(EXERCISES):
        if entry['day'] != day:
            day = entry['day']
            page_break_heading(doc, f'Demi-journée {day}  ·  {DAY_THEMES[day]}', 1)
        build_sheet(doc, index, entry)
    build_key(doc)
    build_recette(doc)
    zoom = doc.settings.element.find(qn('w:zoom'))
    if zoom is not None:
        zoom.set(qn('w:percent'), '100')
    doc.save(str(OUT))
    print(f'written {OUT} ({OUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
