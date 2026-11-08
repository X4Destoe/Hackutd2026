import time
from threading import Event
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.modules import actions, messaging, scenarios
from app.shared import config
from app.shared.store import store
from app.shared.enums import WorkOrderStatus, PlanStatus

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config.settings,'messaging_mode','sim')
    with TestClient(create_app()) as c:
        c.post('/api/demo/reset',json={'scenario_id':'harvey_houston'})
        yield c

def bayou():
    return next(p for p in store.plans.list(building_id='BLD-HOU-01') if p.status==PlanStatus.proposed)

def approve(client):
    plan=bayou();response=client.post(f'/api/plans/{plan.id}/approve',json={'by':'MGR-01'})
    assert response.status_code==200,response.text
    return response.json()

def test_approval_executes_tasks_notices_and_model_change(client):
    before=client.get('/api/portfolio/summary').json()
    plan=approve(client);orders=client.get('/api/workorders?building_id=BLD-HOU-01').json()
    assert plan['status']=='executing' and len(orders)==len(plan['actions'])>0
    assert all(o['status']=='sent' for o in orders)
    assert all('Bayou Plaza' in o['text'] and o['id'] in o['text'] for o in orders)
    messages=client.get('/api/messages').json()
    assert any(m['kind']=='task' and m['work_order_id'] in {o['id'] for o in orders} for m in messages)
    assert any(m['kind']=='tenant_notice' for m in messages)
    assert all(m['channel']=='sim' for m in messages)
    after=client.get('/api/portfolio/summary').json()
    assert after['net_exposure_cents']<before['net_exposure_cents'] and after['avoided_cents']>0

def test_done_reply_closes_target_and_eventually_plan(client):
    plan=approve(client);orders=store.workorders.list(plan_id=plan['id'])
    for order in orders:
        response=client.post('/api/demo/simulate-message',json={'party_id':order.party_id,'text':f'DONE {order.id}'})
        assert response.status_code==200,response.text
        assert store.workorders.require(order.id).status==WorkOrderStatus.done
    assert store.plans.require(plan['id']).status==PlanStatus.done
    assert any(m.kind.value=='task_update' and m.direction.value=='outbound' for m in store.messages.list())

def test_photo_and_blocked_reply(client):
    plan=approve(client);order=store.workorders.list(plan_id=plan['id'])[0]
    client.post('/api/demo/simulate-message',json={'party_id':order.party_id,'text':f'ACCEPTED {order.id}','media_url':'https://example.com/progress.jpg'})
    changed=store.workorders.require(order.id)
    assert changed.status==WorkOrderStatus.accepted and changed.photo_urls==['https://example.com/progress.jpg']
    client.post('/api/demo/simulate-message',json={'party_id':order.party_id,'text':f'BLOCKED {order.id} access gate locked'})
    changed=store.workorders.require(order.id)
    assert changed.status==WorkOrderStatus.blocked and 'gate locked' in changed.updates[-1]

def test_technician_cannot_target_another_party_order(client):
    plan=approve(client);order=store.workorders.list(plan_id=plan['id'])[0]
    assert actions.apply_task_reply('TECH-DAL-01',f'DONE {order.id}',[]) is None
    assert store.workorders.require(order.id).status==WorkOrderStatus.sent

def test_duplicate_approval_does_not_duplicate_side_effects(client):
    plan=approve(client);count=store.workorders.count();messages=store.messages.count()
    assert client.post(f"/api/plans/{plan['id']}/approve",json={'by':'MGR-01'}).status_code==409
    assert store.workorders.count()==count and store.messages.count()==messages

def test_failed_task_is_visible_as_blocked(client,monkeypatch):
    original=messaging.send
    def fail(party,body,kind,**kw):
        return SimpleNamespace(status='failed',channel='sim') if kind=='task' else original(party,body,kind,**kw)
    monkeypatch.setattr(messaging,'send',fail)
    plan=approve(client)
    assert all(o.status==WorkOrderStatus.blocked for o in store.workorders.list(plan_id=plan['id']))
    assert any('failed' in note for o in store.workorders.list(plan_id=plan['id']) for note in o.updates)

def test_missing_tenant_does_not_lose_approved_plan(client):
    building=store.buildings.require('BLD-HOU-01');store.parties.delete(building.tenants[0].contact_party_id or building.tenants[0].id)
    plan=approve(client)
    assert store.workorders.list(plan_id=plan['id'])
    assert any('contact unavailable' in note for o in store.workorders.list(plan_id=plan['id']) for note in o.updates)

def test_manual_completion_and_no_silent_reopen(client):
    plan=approve(client);order=store.workorders.list(plan_id=plan['id'])[0]
    assert client.post(f'/api/workorders/{order.id}/update',json={'status':'done','note':'Operator verified'}).status_code==200
    assert client.post(f'/api/workorders/{order.id}/update',json={'status':'sent'}).status_code==409
    assert client.post('/api/workorders/WO-unknown/update',json={'status':'done'}).status_code==404

def test_live_dispatch_does_not_block_approval(client,monkeypatch):
    entered=Event();release=Event();finished=Event()
    original=messaging.send
    def slow(*args,**kw):
        if args[2]=='task':entered.set();release.wait(2)
        result=original(*args,**kw);finished.set();return result
    monkeypatch.setattr(config.settings,'messaging_mode','photon')
    monkeypatch.setattr(messaging,'send',slow)
    start=time.perf_counter();plan=approve(client)
    try:
        assert time.perf_counter()-start<.3
        assert entered.wait(1)
        assert any(o.status==WorkOrderStatus.created for o in store.workorders.list(plan_id=plan['id']))
    finally:
        release.set();assert finished.wait(2)
        deadline=time.time()+2
        while time.time()<deadline and any(o.status==WorkOrderStatus.created for o in store.workorders.list(plan_id=plan['id'])):time.sleep(.01)

def test_media_never_adds_unsafe_url(client):
    plan=approve(client);order=store.workorders.list(plan_id=plan['id'])[0]
    actions.apply_task_reply(order.party_id,f'ACCEPTED {order.id}',['javascript:alert(1)','https://example.com/photo.jpg','https://example.com/photo.jpg'])
    assert store.workorders.require(order.id).photo_urls==['https://example.com/photo.jpg']


def test_one_combined_notice_per_tenant_contains_all_approved_asks(client):
    plan=approve(client)
    from app.modules.actions import catalog
    building=store.buildings.require('BLD-HOU-01')
    expected=[catalog[action['code']].tenant_notice_text for action in plan['actions'] if catalog[action['code']].tenant_notice_text]
    notices=[m for m in store.messages.list() if m.kind.value=='tenant_notice']
    contacts={t.contact_party_id or t.id for t in building.tenants}
    assert len(notices)==len(contacts)
    assert {m.party_id for m in notices}==contacts
    for message in notices:
        assert all(ask in message.body for ask in expected)
    assert all('relative to impact' not in order.text for order in store.workorders.list(plan_id=plan['id']))


def test_deadline_is_plain_language_without_invented_clock(monkeypatch):
    from app.modules.actions.execute import deadline_label
    monkeypatch.delenv('DEMO_IMPACT_AT',raising=False)
    assert deadline_label(-12,'Houston')=='12 hours before impact'
    assert deadline_label(0,'Dallas')=='at impact'
    assert deadline_label(48,'Fort Myers')=='48 hours after impact'


def test_configured_clock_uses_site_timezone(monkeypatch):
    from app.modules.actions.execute import deadline_label
    monkeypatch.setenv('DEMO_IMPACT_AT','2026-11-08T12:00:00Z')
    assert deadline_label(-12,'Houston')=='by Sat Nov 07 at 18:00 CST (12 hours before impact)'
    assert deadline_label(-12,'Fort Myers')=='by Sat Nov 07 at 19:00 EST (12 hours before impact)'


@pytest.mark.parametrize('value',['not a date','2026-11-08T12:00:00'])
def test_invalid_or_naive_clock_does_not_invent_timezone(monkeypatch,value):
    from app.modules.actions.execute import deadline_label
    monkeypatch.setenv('DEMO_IMPACT_AT',value)
    assert deadline_label(-12,'Houston')=='12 hours before impact'
