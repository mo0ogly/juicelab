"""Regressions for public teaching packs and actual proof/matrix score agreement.

Only isolated SQLite fixture data is written. No lab is contacted, no challenge
is executed and no production roster is used. Scores are checked through the
real proof formatter and cohort aggregator, including the former 97/98 split.
"""
from pathlib import Path
import json
import re
import sys
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'overlay/frontend/src/assets/juicelab'
sys.path.insert(0, str(ROOT / 'dashboard'))
import app as dashboard_app
import db
from proof_routes import build_proof_markdown


def test_active_course_and_guidance():
    """The main course and badge keys agree; all course guidance is bilingual."""
    index = yaml.safe_load((ASSETS / 'selected_challenges.yml').read_text())
    selected = index['selected_challenges']
    badge = (ROOT / 'overlay/frontend/src/app/juicelab-overlay/services/juicelab-badge-engine.service.ts').read_text()
    arrays = badge.split('/** Canonical thirteen-challenge TD')[0]
    keys = re.findall(r"'([A-Za-z]+Challenge)'", arrays)
    assert list(selected) == keys
    assert len(selected) == index['total_challenges'] == 13
    assert [sum(c['demi_journee'] == day for c in selected.values()) for day in (1, 2, 3)] == [5, 4, 4]
    assert 'bullyChatbotChallenge' not in selected
    for key in selected:
        briefing = yaml.safe_load((ASSETS / 'briefing' / f'{key}.yaml').read_text())
        journal = yaml.safe_load((ASSETS / 'journal' / f'{key}.yaml').read_text())
        assert briefing['challenge_key'] == journal['challenge_key'] == key
        for language in ('fr', 'en'):
            assert len(briefing[f'learning_objectives_{language}']) == 2
            assert len(briefing[f'prerequisites_{language}']) == 2
            assert briefing[f'deliverable_{language}'].strip()
            assert journal['journal_prompts'][f'after_solve_{language}'].strip()
            assert journal['journal_prompts'][f'before_solve_{language}'].strip()
        # Candidate guard against reintroducing concrete routes/payloads into
        # public briefing instructions. Semantic review is still required.
        text = yaml.safe_dump(briefing)
        assert not re.search(r'/api/|/rest/|/#/|<iframe|hidden input|#userId', text)


@pytest.mark.parametrize('levels,quiz,flag,expected', [
    (0,100,False,100), (1,100,False,98), (3,100,False,82),
    (5,100,False,50), (5,100,True,60), (0,None,False,None),
])
def test_proof_and_matrix_agree(tmp_path, monkeypatch, levels, quiz, flag, expected):
    """Identical event fixtures yield identical teacher scores, or no final score."""
    monkeypatch.setenv('DASHBOARD_DB', str(tmp_path / 'learning.sqlite'))
    db.init_schema()
    ts = '2026-11-14T10:00:00Z'
    events = []
    costs = [5,10,20,35,50]
    for n, cost in enumerate(costs[:levels], 1):
        events.append({'event_type':'hint_revealed','data':{'level':f'N{n}', 'cost_pct':cost,'consumed_levels':[f'N{i}' for i in range(1,n+1)]},'client_ts':ts,'server_ts':ts})
    events.append({'event_type':'challenge_solved','data':{},'client_ts':ts,'server_ts':ts})
    if quiz is not None:
        events.append({'event_type':'quiz_completed','data':{'score':quiz},'client_ts':ts,'server_ts':ts})
    if flag:
        events.append({'event_type':'flag_verified','data':{},'client_ts':ts,'server_ts':ts})
    with db.get_connection() as connection:
        connection.execute('INSERT INTO cohorts VALUES (?,?,?)', ('fixture','fixture',ts))
        connection.execute('INSERT INTO students (cohort_id,student_token,status,created_at,updated_at) VALUES (?,?,?,?,?)', ('fixture','student','validated',ts,ts))
        for event in events:
            connection.execute('INSERT INTO events(student_token,cohort_id,event_type,challenge_key,data_json,client_ts,server_ts) VALUES (?,?,?,?,?,?,?)', ('student','fixture',event['event_type'],'scoreBoardChallenge',json.dumps(event['data']),ts,ts))
    proof = build_proof_markdown(student_token='student',student_name='Fixture',cohort_id='fixture',challenge_key='scoreBoardChallenge',challenge_name='Score Board',challenge_category='Miscellaneous',challenge_difficulty=1,challenge_description='',events=events)
    total = dashboard_app._cohort_summary('fixture')['totals']['student']
    if expected is None:
        assert total['avg_score'] is None
        assert 'Score final : **' not in proof
    else:
        assert total['avg_score'] == expected
        assert f'Score final : **{expected}/100**' in proof
