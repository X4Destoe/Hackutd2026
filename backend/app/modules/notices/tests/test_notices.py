import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.modules import messaging
from app.shared.config import settings
from app.shared.store import store

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, 'messaging_mode', 'sim')
    with TestClient(create_app()) as c:
        yield c

def payload():
    b = store.buildings.require('BLD-HOU-01')
    return dict(request_id='notice-test-001', scenario_id='harvey_houston', step_hour=-48,
                building_id=b.id, tenant_ids=[b.tenants[0].id], text='Ground floor closed. Reply for assistance.', mode='sim')

def test_selected_audience_and_duplicate(client):
    body = payload()
    r = client.post('/api/customer-notices', json=body)
    assert r.status_code == 200
    messages = r.json()['messages']
    assert len(messages) == 1 and messages[0]['kind'] == 'tenant_notice'
    assert messages[0]['channel'] == 'sim'
    count = store.messages.count()
    r = client.post('/api/customer-notices', json=body)
    assert r.json()['duplicate'] is True and store.messages.count() == count
    body['text'] = 'Different instructions'
    assert client.post('/api/customer-notices', json=body).status_code == 409

def test_wrong_recipient_and_stale_context_send_nothing(client):
    body = payload()
    body['tenant_ids'] = ['not-in-building']
    assert client.post('/api/customer-notices', json=body).status_code == 422
    body = payload(); body['step_hour'] = 0
    assert client.post('/api/customer-notices', json=body).status_code == 409
    body = payload(); body['mode'] = 'photon'
    assert client.post('/api/customer-notices', json=body).status_code == 409
    assert store.messages.count() == 0

def test_photon_failure_visible_and_not_retried(client, monkeypatch):
    from app.modules.messaging import photon
    body = payload()
    party_id = store.buildings.require(body['building_id']).tenants[0].contact_party_id
    party = store.parties.require(party_id)
    monkeypatch.setattr(settings, 'messaging_mode', 'photon')
    monkeypatch.setattr(settings, 'demo_phones', f'{party.phone}:{party_id}')
    calls = []
    def fail(*args):
        calls.append(1)
        raise photon.PhotonError('Provider unavailable')
    monkeypatch.setattr(photon.PhotonChannel, 'send_text', fail)
    body['mode'] = 'photon'
    result = client.post('/api/customer-notices', json=body).json()
    assert result['messages'][0]['status'] == 'failed'
    assert result['messages'][0]['channel'] == 'photon'
    client.post('/api/customer-notices', json=body)
    assert len(calls) == 1

def test_whitespace_and_mixed_audience_rejected(client):
    body = payload(); body['text'] = '  '
    assert client.post('/api/customer-notices', json=body).status_code == 422
    body = payload(); body['tenant_ids'].append('foreign-tenant')
    assert client.post('/api/customer-notices', json=body).status_code == 422
    assert store.messages.count() == 0

def test_photon_acceptance_and_verified_customer_reply(client, monkeypatch):
    import hashlib, hmac, json, time
    from app.modules.messaging import photon
    body = payload()
    party_id = store.buildings.require(body['building_id']).tenants[0].contact_party_id
    phone = store.parties.require(party_id).phone
    monkeypatch.setattr(settings, 'messaging_mode', 'photon')
    monkeypatch.setattr(settings, 'demo_phones', f'{phone}:{party_id}')
    monkeypatch.setattr(photon, 'settings', lambda: photon.PhotonSettings(spectrum_webhook_secret='local-test-only'))
    sent = []
    monkeypatch.setattr(photon.PhotonChannel, 'send_text', lambda self, to, text, media: sent.append((to, text)) or 'provider-ack')
    body['mode'] = 'photon'
    result = client.post('/api/customer-notices', json=body).json()
    assert result['messages'][0]['status'] == 'sent'
    assert sent[0][0] == phone and 'Bayou Plaza' in sent[0][1]
    raw = json.dumps({'event':'message.received', 'message':{'id':'tenant-reply-unique', 'sender':{'id':phone}, 'content':{'type':'text','text':'Received, relocating equipment'}}}).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(b'local-test-only', b'v0:'+timestamp.encode()+b':'+raw, hashlib.sha256).hexdigest()
    headers = {'X-Spectrum-Event':'message.received','X-Spectrum-Timestamp':timestamp,'X-Spectrum-Signature':'v0='+signature,'X-Spectrum-Webhook-Id':'tenant-delivery-unique'}
    assert client.post('/api/webhooks/photon', content=raw, headers=headers).status_code == 200
    assert any(m.party_id == party_id and m.direction == 'inbound' for m in store.messages.list())


@pytest.mark.parametrize('change', ['reset', 'timeline', 'mode'])
def test_context_change_after_first_attempt_cancels_remaining_recipients(client, monkeypatch, change):
    from app.modules import scenarios
    body = payload()
    building = store.buildings.require(body['building_id'])
    body['tenant_ids'] = [tenant.id for tenant in building.tenants]
    assert len(body['tenant_ids']) > 1
    original = messaging.send
    calls = []
    def send_then_change(*args, **kwargs):
        calls.append(args[0])
        result = original(*args, **kwargs)
        if change == 'reset':
            scenarios.load('uri_dallas')
        elif change == 'timeline':
            scenarios.set_hour(0)
        else:
            monkeypatch.setattr(settings, 'messaging_mode', 'photon')
        return result
    monkeypatch.setattr(messaging, 'send', send_then_change)
    response = client.post('/api/customer-notices', json=body)
    assert response.status_code == 409
    assert 'Remaining recipients were cancelled' in response.json()['detail']
    assert len(calls) == 1
    if change == 'reset':
        assert store.messages.list() == []
