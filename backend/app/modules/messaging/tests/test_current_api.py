import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging
from app.modules.messaging import current_api, photon
from app.shared.config import settings
from app.shared.store import store

PROJECT = 'pho_prj_test'
KEY = 'unit-test-credential'
SECRET = 'whsec_' + base64.b64encode(b'unit-test-signing-key').decode()
PHONE = '+12145550123'


@pytest.fixture
def cfg(monkeypatch):
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key=KEY, photon_project_id=PROJECT,
        photon_webhook_secret=SECRET, demo_phones=PHONE+':TECH-HOU-01', photon_claims_alert_phone='')
    monkeypatch.setattr(photon, 'settings', lambda: cfg)
    return cfg


def signed(payload, identity='event-1', stamp=None):
    raw = json.dumps(payload).encode()
    stamp = str(int(time.time()) if stamp is None else stamp)
    sig = base64.b64encode(hmac.new(b'unit-test-signing-key', identity.encode()+b'.'+stamp.encode()+b'.'+raw, hashlib.sha256).digest()).decode()
    return raw, {'webhook-id':identity, 'webhook-timestamp':stamp, 'webhook-signature':'v1,'+sig, 'content-type':'application/json'}


def event(text='progress', mid='message-1'):
    return {'apiVersion':current_api.API_VERSION, 'type':'message.received', 'data':{'object':{
        'id':mid, 'projectId':PROJECT, 'platform':'imessage', 'status':'received',
        'space':{'id':'space-1', 'kind':'direct'}, 'sentBy':{'id':'user-1','handle':PHONE},
        'receivedBy':{'id':'agent-1'}, 'content':{'type':'text','text':text}}}}


def transport(cfg, change=None, failure=None):
    requests=[]
    def reply(req):
        requests.append(req)
        assert req.url.host == 'api.photon.codes'
        assert req.headers['authorization'] == 'Bearer '+KEY
        assert req.url.path.startswith('/v1/projects/'+PROJECT)
        suffix=req.url.path.split(PROJECT,1)[1]
        if failure: return failure(req)
        if suffix == '/users' and req.method == 'GET':
            data={'items':[{'id':'agent-1','projectId':PROJECT,'platform':'imessage','kind':'agent','details':{'resourceId':'line-1'}}]}; code=200
        elif suffix == '/users':
            assert json.loads(req.content)=={'platform':'imessage','handle':PHONE}
            data={'id':'user-1','projectId':PROJECT,'platform':'imessage','handle':PHONE};code=201
        elif suffix == '/spaces' and req.method == 'GET':
            data={'items':[]};code=200
        elif suffix == '/spaces':
            assert json.loads(req.content)['participantIds']==['agent-1','user-1']
            assert req.headers['idempotency-key']
            data={'id':'space-1','projectId':PROJECT,'platform':'imessage','kind':'direct','participantIds':['agent-1','user-1']};code=201
        elif suffix == '/messages':
            assert json.loads(req.content)=={'senderId':'agent-1','spaceId':'space-1','content':{'type':'text','format':'plain','text':'hello'}}
            assert req.headers['idempotency-key']
            data={'id':'message-out','projectId':PROJECT,'status':'dispatched'};code=202
        else: raise AssertionError('Unexpected request')
        if change: code,data=change(suffix,code,data)
        return httpx.Response(code,json=data)
    return httpx.Client(transport=httpx.MockTransport(reply)),requests


def test_current_send_uses_documented_auth_identities_and_ack(cfg):
    client, requests=transport(cfg)
    assert photon.PhotonChannel(client, cfg).send_text(PHONE,'hello',[])=='message-out'
    assert len(requests)==5
    assert KEY not in repr(cfg)


def test_unmapped_recipient_and_missing_project_never_contact_provider(cfg):
    client, requests=transport(cfg)
    with pytest.raises(photon.PhotonError,match='DEMO_PHONES'):
        photon.PhotonChannel(client,cfg).send_text('+12145550199','hello',[])
    cfg.photon_project_id=''
    with pytest.raises(photon.PhotonError,match='project ID'):
        photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])
    assert requests==[]


@pytest.mark.parametrize('status,payload',[(200,{'id':'x','projectId':PROJECT,'status':'dispatched'}),(202,{'id':'x','projectId':PROJECT,'status':'failed'}),(202,{'status':'accepted'}),(202,{'id':'x','projectId':'other','status':'accepted'})])
def test_invalid_acknowledgements_cannot_claim_success(cfg,status,payload):
    client, requests=transport(cfg,lambda suffix,code,data:(status,payload) if suffix=='/messages' else (code,data))
    with pytest.raises(photon.PhotonError,match='acknowledge'):
        photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])
    assert len(requests)==5


def test_http_refusal_and_error_bodies_do_not_leak_secrets_or_retry(cfg):
    client, requests=transport(cfg,failure=lambda req:httpx.Response(403,json={'error':KEY}))
    with pytest.raises(photon.PhotonError) as exc:
        photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])
    assert KEY not in str(exc.value) and len(requests)==1


def test_standard_webhook_valid_tampered_old_and_rotated_signature(cfg):
    raw,headers=signed(event())
    assert photon.PhotonChannel(config=cfg).parse_inbound(raw,headers)==(PHONE,'progress',[])
    assert not current_api.verify(raw+b' ',headers,SECRET)
    old,h=signed(event(),stamp=int(time.time())-301)
    assert not current_api.verify(old,h,SECRET)
    assert not current_api.verify(raw,headers,'invalid')
    assert current_api.verify(raw,{**headers,'webhook-signature':'v1,wrong '+headers['webhook-signature']},SECRET)


@pytest.mark.parametrize('field,value,exception',[('projectId','other',PermissionError),('sentBy',[],ValueError),('content',{'type':'text','text':[]},ValueError)])
def test_signed_malformed_or_wrong_project_is_rejected(cfg,field,value,exception):
    payload=event();payload['data']['object'][field]=value
    with pytest.raises(exception):photon.PhotonChannel(config=cfg).parse_inbound(*signed(payload))


def test_version_groups_signals_and_outgoing_are_not_chat_turns(cfg):
    p=event();p['apiVersion']='future'
    with pytest.raises(ValueError):photon.PhotonChannel(config=cfg).parse_inbound(*signed(p))
    for path,value in [('status','dispatched'),('space',{'id':'s','kind':'group'}),('content',{'type':'message.read'})]:
        p=event();p['data']['object'][path]=value
        assert photon.PhotonChannel(config=cfg).parse_inbound(*signed(p)) is None


def test_current_webhook_duplicate_message_with_new_delivery_runs_once(cfg,monkeypatch):
    monkeypatch.setattr(settings,'messaging_mode','photon')
    monkeypatch.setattr(settings,'demo_phones',PHONE+':TECH-HOU-01')
    with TestClient(create_app()) as client:
        first,h=signed(event(mid='modern-once'),identity='modern-delivery-1')
        second,h2=signed(event(mid='modern-once'),identity='modern-delivery-2')
        assert client.post('/api/webhooks/photon',content=first,headers=h).status_code==200
        result=client.post('/api/webhooks/photon',content=second,headers=h2)
        assert result.status_code==200 and result.json()['duplicate']
        assert len(store.messages.list(direction='inbound'))==1


def test_manager_mapping_and_claims_alert_recipient(cfg,monkeypatch):
    # Fixture numbers only; the user's real phone settings are never used by tests.
    manager='+12145550124'
    monkeypatch.setattr(settings,'messaging_mode','sim')
    monkeypatch.setattr(settings,'demo_phones',manager+':MGR-01,'+PHONE+':TECH-HOU-01')
    cfg.photon_claims_alert_phone=PHONE
    with TestClient(create_app()) as client:
        assert messaging.party_for_phone(manager).id=='MGR-01'
        r=client.post('/api/demo/simulate-message',json={'phone':'+12145550125','text':'I need to file an insurance claim'})
        assert r.status_code==200
        alerts=[m for m in store.messages.list(party_id='TECH-HOU-01') if 'claims-assistance request' in m.body]
        assert len(alerts)==1 and alerts[0].channel=='sim'
        assert alerts[0].referral_id and len(alerts[0].body)<=320


def test_ignored_event_does_not_suppress_later_received_message(cfg, monkeypatch):
    monkeypatch.setattr(settings, 'messaging_mode', 'photon')
    monkeypatch.setattr(settings, 'demo_phones', PHONE+':TECH-HOU-01')
    with TestClient(create_app()) as client:
        payload=event(mid='ignored-then-received');payload['type']='message.updated'
        raw,headers=signed(payload,identity='ignored-first')
        assert client.post('/api/webhooks/photon',content=raw,headers=headers).json()['ignored']
        raw,headers=signed(event(mid='ignored-then-received'),identity='received-second')
        result=client.post('/api/webhooks/photon',content=raw,headers=headers)
        assert result.status_code==200 and not result.json().get('duplicate')
        assert len(store.messages.list(direction='inbound'))==1


def test_gateway_only_exposes_webhook_and_preserves_signed_bytes(monkeypatch, cfg):
    from app.modules.messaging import webhook_gateway
    seen=[]
    raw, headers = signed({'signed': True}, identity='test-delivery')
    monkeypatch.setattr(webhook_gateway, 'settings', lambda: cfg)
    original=httpx.AsyncClient
    def upstream(request):
        seen.append(request)
        assert request.url == 'http://127.0.0.1:8000/api/webhooks/photon'
        assert request.content == raw
        assert request.headers['webhook-id']=='test-delivery'
        assert 'authorization' not in request.headers
        return httpx.Response(200,json={'ok':True})
    def factory(**kwargs):
        assert kwargs['trust_env'] is False
        return original(**kwargs,transport=httpx.MockTransport(upstream))
    monkeypatch.setattr(webhook_gateway.httpx,'AsyncClient',factory)
    with TestClient(webhook_gateway.app) as client:
        assert client.get('/api/messages').status_code==404
        assert client.get('/docs').status_code==404
        assert client.get('/openapi.json').status_code==404
        assert client.post('/api/webhooks/photon', content=raw).status_code==401
        result=client.post('/api/webhooks/photon',content=raw,headers={**headers,'Authorization':'not-forwarded'})
        assert result.status_code==200 and len(seen)==1
        assert client.post('/api/webhooks/photon',content=b'x'*1048577).status_code==413
        assert len(seen)==1


def test_sender_discovery_uses_owned_resource_not_an_invented_kind_enum(cfg):
    def native_kind(suffix,code,data):
        if suffix=='/users' and 'items' in data:
            data['items'][0]['kind']='phone'
        return code,data
    client,_=transport(cfg,native_kind)
    assert photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])=='message-out'


def test_signed_manager_to_technician_to_claims_current_api_loop(cfg,monkeypatch):
    """Full public webhook -> app workflow -> current Photon API, with provider I/O mocked."""
    manager, resident = '+12145550126', '+12145550127'
    mapping=manager+':MGR-01,'+PHONE+':TECH-HOU-01,'+resident+':RESIDENT-0127'
    cfg.demo_phones=mapping; cfg.photon_claims_alert_phone=PHONE
    monkeypatch.setattr(settings,'messaging_mode','photon')
    monkeypatch.setattr(settings,'demo_phones',mapping)
    sends=[]
    def provider(self,method,suffix,*,body=None,params=None,idempotency=None):
        if suffix=='/users' and method=='GET':
            return 200,{'items':[{'id':'agent-1','projectId':PROJECT,'platform':'imessage','details':{'resourceId':'line-1'}}]}
        if suffix=='/users':
            return 201,{'id':'peer-'+body['handle'][-4:],'projectId':PROJECT,'platform':'imessage','handle':body['handle']}
        if suffix=='/spaces' and method=='GET':
            return 200,{'items':[]}
        if suffix=='/spaces':
            return 201,{'id':'space-'+body['participantIds'][1],'projectId':PROJECT,'platform':'imessage','kind':'direct','participantIds':body['participantIds']}
        assert suffix=='/messages' and method=='POST'
        sends.append(body)
        return 202,{'id':'accepted-'+str(len(sends)),'projectId':PROJECT,'status':'dispatched'}
    monkeypatch.setattr(current_api.CurrentPhoton,'request',provider)
    with TestClient(create_app()) as client:
        payload=event('YES PLAN-001',mid='full-manager');payload['data']['object']['sentBy']['handle']=manager
        raw,headers=signed(payload,identity='full-manager-delivery')
        assert client.post('/api/webhooks/photon',content=raw,headers=headers).status_code==200
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            tasks=store.workorders.list()
            if tasks and all(t.status=='sent' for t in tasks):break
            time.sleep(.01)
        assert tasks and all(t.status=='sent' for t in tasks)
        raw,headers=signed(event('DONE '+tasks[0].id,mid='full-tech'),identity='full-tech-delivery')
        assert client.post('/api/webhooks/photon',content=raw,headers=headers).status_code==200
        assert store.workorders.require(tasks[0].id).status=='done'
        payload=event('I need to file an insurance claim',mid='full-claim');payload['data']['object']['sentBy']['handle']=resident
        raw,headers=signed(payload,identity='full-claim-delivery')
        assert client.post('/api/webhooks/photon',content=raw,headers=headers).status_code==200
        assert any('claims-assistance request' in s['content']['text'] for s in sends)
        count=len(sends)
        assert client.post('/api/webhooks/photon',content=raw,headers=headers).json()['duplicate']
        assert len(sends)==count
        assert any(m.channel=='photon' and m.status=='sent' for m in store.messages.list())


@pytest.mark.parametrize('shared',[False,True])
def test_existing_direct_space_is_reused_for_dedicated_or_shared_agent(cfg,shared):
    def existing(suffix,code,data):
        if shared and suffix=='/users' and 'items' in data:
            data['items'][0]['details']={'type':'shared'}
        if suffix=='/spaces' and 'items' in data:
            data['items']=[{'id':'space-1','projectId':PROJECT,'platform':'imessage','kind':'direct','participantIds':['user-1','agent-1']}]
        return code,data
    client,requests=transport(cfg,existing)
    assert photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])=='message-out'
    assert not any(r.method=='POST' and r.url.path.endswith('/spaces') for r in requests)


def test_shared_without_existing_space_gives_assignment_inbound_guidance(cfg):
    def shared(suffix,code,data):
        if suffix=='/users' and 'items' in data:data['items'][0]['details']={'type':'shared'}
        return code,data
    client,requests=transport(cfg,shared)
    with pytest.raises(photon.PhotonError,match='Text the Photon agent number'):
        photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])
    assert not any(r.url.path.endswith('/messages') for r in requests)


@pytest.mark.parametrize('code',[403,404,422])
def test_space_creation_refusal_has_actionable_setup_message(cfg,code):
    client,requests=transport(cfg,lambda suffix,status,data:(code,{}) if suffix=='/spaces' and 'items' not in data else (status,data))
    with pytest.raises(photon.PhotonError,match='iMessage > senders'):
        photon.PhotonChannel(client,cfg).send_text(PHONE,'hello',[])
    assert not any(r.url.path.endswith('/messages') for r in requests)
