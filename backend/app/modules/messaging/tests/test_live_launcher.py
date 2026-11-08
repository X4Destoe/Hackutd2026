from app.modules.messaging import live, photon
from app.shared.config import settings


def config(monkeypatch):
    cfg=photon.PhotonSettings(_env_file=None, photon_api_key='test-key',photon_project_id='pho_prj_test',
        photon_webhook_secret='whsec_dGVzdA==',demo_phones='+12145550123:MGR-01')
    monkeypatch.setattr(live,'photon_settings',lambda:cfg)
    return cfg


def test_failed_preflight_never_sends_or_starts_backend(monkeypatch,capsys):
    config(monkeypatch)
    class Unreachable:
        def __init__(self,cfg):pass
        def request(self,*args):raise photon.PhotonError('Photon API unreachable before message send.')
    monkeypatch.setattr(live,'CurrentPhoton',Unreachable)
    monkeypatch.setattr(live,'_ports_available',lambda:None)
    monkeypatch.setattr(live.subprocess,'Popen',lambda *args,**kw:(_ for _ in ()).throw(AssertionError('Must not start')))
    assert live.main([])==1
    assert 'did not start' in capsys.readouterr().err


def test_explicit_test_sends_once_and_never_starts_services(monkeypatch,capsys):
    config(monkeypatch); sent=[]
    class Ready:
        def __init__(self,cfg):pass
        def request(self,*args):return 200,{}
        def sender(self):return 'agent-test'
        def send(self,phone,text):sent.append((phone,text));return 'provider-message-test'
    monkeypatch.setattr(live,'CurrentPhoton',Ready)
    assert live.main(['--test-party','MGR-01'])==0
    assert len(sent)==1 and sent[0][0]=='+12145550123'
    assert 'Handset delivery is not yet confirmed' in capsys.readouterr().out
    assert live.main(['--test-party','UNKNOWN'])==1
    assert len(sent)==1


def test_live_start_sets_real_mode_and_cleans_up_gateway(monkeypatch):
    config(monkeypatch); calls=[]
    monkeypatch.setattr(settings,'messaging_mode','sim')
    monkeypatch.setenv('MESSAGING_MODE','sim')
    class Ready:
        def __init__(self,cfg):pass
        def request(self,*args):return 200,{}
        def sender(self):return 'agent-test'
    class Child:
        def __init__(self,*args,**kw):calls.append(args[0])
        def poll(self):return None
        def terminate(self):calls.append('terminate')
        def wait(self,timeout=None):calls.append('wait')
    monkeypatch.setattr(live,'CurrentPhoton',Ready)
    monkeypatch.setattr(live,'_ports_available',lambda:None)
    monkeypatch.setattr(live.subprocess,'Popen',Child)
    def run(*args,**kwargs):
        assert settings.messaging_mode=='photon'
        assert kwargs=={'host':'127.0.0.1','port':8000}
        calls.append('api-started')
    monkeypatch.setattr(live.uvicorn,'run',run)
    assert live.main([])==0
    assert 'app.modules.messaging.webhook_gateway:app' in calls[0]
    assert calls[-3:]==['api-started','terminate','wait']
