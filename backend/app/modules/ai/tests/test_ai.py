import time
from threading import Event
import pytest
from app.modules import ai

@pytest.fixture(autouse=True)
def templates_only(monkeypatch):
    monkeypatch.setattr(ai.config.settings, 'llm_provider', 'none')

@pytest.mark.parametrize('text,language,need,people,urgent', [
    ('our apartment flooded, 2 kids, need a dry place', 'en', 'shelter', 3, False),
    ('mi papá usa oxígeno y no hay luz', 'es', 'medical', 1, True),
    ('we are 5 people and need water', 'en', 'food_water', 5, False),
    ('somos 4 personas con frío', 'es', 'warmth', 4, False),
    ('nhà bị ngập, 2 trẻ cần chỗ ở', 'vi', 'shelter', 3, False),
    ('trời lạnh cần sưởi', 'vi', 'warmth', 1, False),
    ('my roof needs repair and I need a claim', 'en', 'repair', 1, False),
    ('hello', 'en', 'info', 1, False),
])
def test_classification(text, language, need, people, urgent):
    result = ai.classify_need(text, language)
    assert need in result['needs'] and result['people'] == people
    assert result['language'] == language and result['urgent'] == urgent
    assert len(result['summary']) <= 100

@pytest.mark.parametrize('language', ['en', 'es', 'vi'])
@pytest.mark.parametrize('purpose', ['redirect', 'reroute', 'ack'])
def test_resident_messages(language, purpose):
    facts = {'site_name': 'Convention Center', 'address': '1001 Avenida de las Americas', 'details': 'Open, 310 spots left.'}
    message = ai.compose(purpose, facts, language)
    assert 0 < len(message) <= 320
    if purpose != 'ack': assert facts['address'] in message

def test_task_and_report():
    message = ai.compose('task', {'work_order_id': 'WO-001', 'building_name': 'Bayou Plaza', 'task_text': 'Deploy barriers by 18:00.'})
    assert all(s in message for s in ['WO-001', 'Bayou Plaza', '18:00', 'DONE', 'BLOCKED'])
    facts = {'building_name': 'Bayou Plaza', 'cost_cents': 2400000, 'avoided_cents': 98000000}
    assert '$24k' in ai.rationale(facts) and '$980k' in ai.rationale(facts)
    report = ai.write_report('executive_summary', facts)
    assert 'Bayou Plaza' in report and '$980,000.00' in report and 'synthetic' in report

def test_long_address_not_truncated():
    result = ai.compose('redirect', {'address': '123 Main', 'site_name': 'x' * 300, 'details': 'y' * 300}, 'es')
    assert '123 Main' in result and len(result) <= 320
    with pytest.raises(ValueError, match='320'): ai.compose('redirect', {'address': 'a' * 321})

class Fake:
    def json(self, *args): raise ConnectionError('unavailable')
    def text(self, *args): raise ConnectionError('unavailable')

def test_failed_provider(monkeypatch):
    monkeypatch.setattr(ai, '_provider', lambda: Fake())
    start = time.monotonic()
    assert 'shelter' in ai.classify_need('flooded')['needs']
    assert '123 Main' in ai.compose('redirect', {'address': '123 Main'})
    assert time.monotonic() - start < 6

def test_invalid_classification(monkeypatch):
    class Invalid(Fake):
        def json(self, *args): return {'needs': ['invented'], 'people': -2}
    monkeypatch.setattr(ai, '_provider', lambda: Invalid())
    assert ai.classify_need('2 kids flooded')['people'] == 3

def test_provider_losing_address(monkeypatch):
    class Wrong(Fake):
        def text(self, *args): return 'Go to a different location.'
    monkeypatch.setattr(ai, '_provider', lambda: Wrong())
    assert '123 Main' in ai.compose('redirect', {'address': '123 Main'})

def test_deadline_and_bounded_workers(monkeypatch):
    release = Event()
    class Stalled(Fake):
        def json(self, *args):
            release.wait(2)
            return {}
    monkeypatch.setattr(ai, '_provider', lambda: Stalled())
    monkeypatch.setattr(ai, 'TIMEOUT_SECONDS', .05)
    try:
        start = time.monotonic()
        assert ai.classify_need('cold')['needs'] == ['warmth']
        assert ai.classify_need('flooded')['needs'] == ['shelter']
        assert time.monotonic() - start < .5
    finally:
        release.set()
        assert ai._slot.acquire(timeout=1)
        ai._slot.release()

def test_missing_key(monkeypatch):
    monkeypatch.setattr(ai.config.settings, 'llm_provider', 'openai')
    monkeypatch.setattr(ai.config.settings, 'openai_api_key', '')
    assert ai.provider_name() == 'templates'

def test_valid_classification_keeps_medical_urgency(monkeypatch):
    class Valid(Fake):
        def json(self, *args):
            return {'needs': ['info'], 'people': 1, 'urgent': False, 'language': 'es', 'summary': 'Needs assistance'}
    monkeypatch.setattr(ai, '_provider', lambda: Valid())
    result = ai.classify_need('mi papá usa oxígeno y no hay luz')
    assert result['urgent'] and 'medical' in result['needs']

def test_valid_provider_text_used(monkeypatch):
    class Valid(Fake):
        def text(self, *args): return 'Please go to 123 Main.'
    monkeypatch.setattr(ai, '_provider', lambda: Valid())
    assert ai.compose('redirect', {'address': '123 Main'}) == 'Please go to 123 Main.'


@pytest.mark.parametrize('cents,expected', [(0, '$0'), (1, '$0.01'), (125050, '$1.25k'), (2400000, '$24k'), (98000000, '$980k'), (165000000, '$1.65M'), (-2400000, '$-24k')])
def test_compact_dollars(cents, expected):
    assert ai.templates.compact_dollars(cents) == expected


def test_nested_report_facts_allow_prose_without_dict_repr(monkeypatch):
    class Valid(Fake):
        def text(self, *args):
            return 'At 123 Main, the portfolio has $980k exposure. Prioritize response.'
    monkeypatch.setattr(ai, '_provider', lambda: Valid())
    facts = {'portfolio': {'net_exposure_cents': 98000000}, 'buildings': [{'address': '123 Main', 'drivers': ['grid down', 'generator empty']}]}
    assert ai.write_report('executive_summary', facts).startswith('At 123 Main')


@pytest.mark.parametrize('output', ['Exposure is $24k.', 'Exposure is $980k0 at 123 Main.', 'Exposure is $980k.'])
def test_report_missing_or_changed_money_address_falls_back(monkeypatch, output):
    class Wrong(Fake):
        def text(self, *args): return output
    monkeypatch.setattr(ai, '_provider', lambda: Wrong())
    facts = {'rows': [{'address': '123 Main', 'net_exposure_cents': 98000000}]}
    assert ai.write_report('executive_summary', facts).startswith('# Executive summary')


def test_tenant_report_checks_nested_money(monkeypatch):
    class Valid(Fake):
        def text(self, *args): return 'Estimated loss $24,000 at 123 Main.'
    monkeypatch.setattr(ai, '_provider', lambda: Valid())
    assert ai.write_report('tenant_notice', {'nested': {'cost_cents': 2400000, 'address': '123 Main'}}).startswith('Estimated loss')


def test_team_default_and_model_override(monkeypatch):
    monkeypatch.setattr(ai.config.settings, 'llm_provider', 'anthropic')
    monkeypatch.setattr(ai.config.settings, 'anthropic_api_key', 'dummy-not-used')
    monkeypatch.setattr(ai.config.settings, 'llm_model', '')
    assert ai.provider_name() == 'anthropic:claude-sonnet-5-5'
    monkeypatch.setattr(ai.config.settings, 'llm_model', 'team-override')
    assert ai.provider_name() == 'anthropic:team-override'
