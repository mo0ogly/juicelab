"""Append matching teaching guidance to existing JuiceLab Word handouts.

Use the bundled document Python runtime. The two existing handouts retain their
exercise instructions, figures and internal links. Student assessment and teacher
answers stay in separate files. Markdown sources in docs/ are authoritative for
new sections. Does not render: final delivery requires render_docx.py and review.
"""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import os
import re
from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
MARKERS = {'student': 'Évaluer son raisonnement avant et après JuiceLab',
           'teacher': 'Accompagner et évaluer le parcours JuiceLab'}


def _plain(text):
    """Preserve Markdown link labels and destinations as readable Word text."""
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1 (\2)', text)


def append_teaching_sections(document, audience):
    """Append the audience's Markdown guide once, preserving existing content.

    Requires audience student/teacher and a python-docx Document. Returns whether
    sections were added; an existing title makes this a no-op. Raises on invalid
    audience, missing source or malformed table before the caller saves output.
    Does not write files, score students or certify layout or technical recipe.
    """
    marker = MARKERS[audience]
    if any(p.text == marker for p in document.paragraphs):
        return False
    source = ROOT / 'docs' / ('ASSESSMENT-FR.md' if audience == 'student' else 'TEACHER-GUIDE-FR.md')
    lines = source.read_text().splitlines()
    paragraph = []
    table_rows = []

    def flush_paragraph():
        """Append accumulated prose as one paragraph; clear the local buffer."""
        if paragraph:
            document.add_paragraph(_plain(' '.join(paragraph)))
            paragraph.clear()

    def flush_table():
        """Append a rectangular rubric table with a repeating header row."""
        if not table_rows:
            return
        count = len(table_rows[0])
        assert all(len(row) == count for row in table_rows)
        table = document.add_table(rows=0, cols=count)
        table.style = 'Table Grid'
        for row in table_rows:
            for cell, content in zip(table.add_row().cells, row):
                cell.text = _plain(content)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
        from docx.oxml import OxmlElement
        header = OxmlElement('w:tblHeader')
        table.rows[0]._tr.get_or_add_trPr().append(header)
        table_rows.clear()

    for line in lines:
        if line.startswith('|'):
            flush_paragraph()
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                table_rows.append(cells)
            continue
        flush_table()
        if line.startswith('#'):
            flush_paragraph()
            level = len(line) - len(line.lstrip('#'))
            heading = document.add_heading(line[level:].strip(), min(level, 3))
            if level == 1:
                heading.paragraph_format.page_break_before = True
        elif not line.strip():
            flush_paragraph()
        elif re.match(r'^\d+\.\s', line):
            flush_paragraph()
            paragraph.append(line.strip())
        else:
            paragraph.append(line.strip())
    flush_paragraph()
    flush_table()
    return True


def atomic_save(document, target):
    """Serialize and check a Word ZIP, flush then atomically replace its target.

    Existing output survives serialization and write failures before replacement.
    Directory fsync errors propagate; they do not imply replacement was undone.
    This is a structural write guard, not a render/visual quality check.
    """
    buffer = BytesIO()
    document.save(buffer)
    data = buffer.getvalue()
    with ZipFile(BytesIO(data)) as archive:
        assert archive.testzip() is None
    temporary = target.with_name(target.name + '.pending')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    fd = os.open(target.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    """Back up each active Word, append guidance and write review candidates.

    Outputs candidates in the evidence folder; active docs/ handouts are not
    replaced. Missing inputs or an existing conflicting backup propagate errors.
    Installation follows separate structural and visual validation.
    """
    evidence = ROOT / '.swarm-fixtures/pedagogy-20261114'
    for audience, name in [('student', 'OWASP-JuiceLab-TD-Eleves.docx'),
                           ('teacher', 'OWASP-JuiceLab-Recette-Prof.docx')]:
        original = ROOT / 'docs' / name
        backup = evidence / 'before/docs' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(original.read_bytes())
        document = Document(original)
        append_teaching_sections(document, audience)
        atomic_save(document, evidence / name)
        print('Candidate:', name)


if __name__ == '__main__':
    main()
