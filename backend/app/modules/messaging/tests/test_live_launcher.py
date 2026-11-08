import asyncio
import pytest
from app.modules.messaging import live, photon
from app.shared.config import settings
from app.shared.store import store


def config(monkeypatch,secret=''):
    cfg=photon.PhotonSettings(_env_file=None,photon_api_key='test-key',photon_project_id='pho_prj_test',
        photon_webhook_secret=secret,spectrum_webhook_secret='',demo_phones='+12145550123:MGR-01')
    monkeypatch.setattr(live,'photon_settings',lambda:cfg)
    return cfg


class Ready:
    def __init__(self,cfg):pass
    def agents(self):return {'agent-one':{},'agent-two':{}}
    def request(self,*args,**kwargs):return 200,{'items':[]}


def test_failed_preflight_never_sends_or_starts_backend(monkeypatch,capsys):
    config(monkeypatch)
    class Unreachable(Ready):
        def agents(self):raise photon.PhotonError('Photon API unreachable before message send.')
    monkeypatch.setattr(live,'CurrentPhoton',Unreachable)
    monkeypatch.setattr(live,'_ports_available',lambda **kw:None)
    monkeypatch.setattr(live.uvicorn,'run',lambda *args,**kw:(_ for _ in ()).throw(AssertionError('Must not start')))
    assert live.main([])==1
    assert 'did not start' in capsys.readouterr().err


def test_explicit_test_sends_once_and_never_starts_services(monkeypatch,capsys):
    config(monkeypatch);sent=[]
    class Sender(Ready):
        def send(self,phone,text):sent.append((phone,text));return 'provider-message-test'
    monkeypatch.setattr(live,'CurrentPhoton',Sender)
    assert live.main(['--test-party','MGR-01'])==0
    assert len(sent)==1 and sent[0][0]=='+12145550123'
    assert 'Handset delivery is not yet confirmed' in capsys.readouterr().out
    assert live.main(['--test-party','UNKNOWN'])==1 and len(sent)==1


def test_polling_starts_after_seed_without_secret_or_tunnel(monkeypatch):
    config(monkeypatch);calls=[]
    monkeypatch.setattr(settings,'messaging_mode','sim');monkeypatch.setenv('MESSAGING_MODE','sim')
    monkeypatch.setattr(live,'CurrentPhoton',Ready)
    monkeypatch.setattr(live,'_ports_available',lambda **kw:None)
    class Poller:
        def start(self):
            assert store.buildings.count()>0
            assert settings.messaging_mode=='photon'
            calls.append('poll-started')
        def stop(self):calls.append('poll-stopped')
    monkeypatch.setattr(live,'_poller',lambda cfg:Poller())
    monkeypatch.setattr(live.subprocess,'Popen',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No gateway by default')))
    def run(app,**kwargs):
        assert kwargs=={'host':'127.0.0.1','port':8000}
        async def serve():
            async with app.router.lifespan_context(app):calls.append('api-started')
        asyncio.run(serve())
    monkeypatch.setattr(live.uvicorn,'run',run)
    assert live.main([])==0
    assert calls==['poll-started','api-started','poll-stopped']


def test_webhook_receiver_requires_secret(monkeypatch):
    config(monkeypatch)
    monkeypatch.setattr(live,'_ports_available',lambda **kw:None)
    assert live.main(['--webhook'])==1


def test_gateway_failure_is_detected_and_child_cleaned(monkeypatch):
    calls=[]
    class Child:
        def __init__(self,*a,**kw):pass
        def poll(self):return None
        def terminate(self):calls.append('terminate')
        def wait(self,timeout=None):calls.append('wait')
    monkeypatch.setattr(live.subprocess,'Popen',Child)
    monkeypatch.setattr(live,'_wait_for_gateway',lambda p:(_ for _ in ()).throw(photon.PhotonError('startup failed')))
    with pytest.raises(photon.PhotonError):live.GatewayReceiver().start()
    assert calls==['terminate','wait']
