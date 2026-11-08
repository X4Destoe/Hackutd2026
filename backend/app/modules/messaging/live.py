"""Local real texting: python -m app.modules.messaging.live.
Replies are polled by default (no public tunnel). --webhook uses signed ingress instead.
--test-party MGR-01 sends one explicit test and exits.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
import socket
import subprocess
import sys
import threading
import time

import uvicorn

from app.shared.config import settings as app_settings
from .current_api import CurrentPhoton, E164
from .photon import PhotonError, settings as photon_settings

log = logging.getLogger('messaging.live')


def _ports_available(webhook=False):
    for port in ((8000, 8788) if webhook else (8000,)):
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise PhotonError(f'Port {port} is already in use. Stop the existing local service before starting live messaging.') from exc


def _wait_for_gateway(process, timeout=5):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise PhotonError('Webhook receiver exited during startup; the API was not started.')
        try:
            with socket.create_connection(('127.0.0.1',8788),timeout=.1):
                return
        except OSError:
            time.sleep(.05)
    raise PhotonError('Webhook receiver did not become ready; the API was not started.')


class GatewayReceiver:
    def __init__(self):
        self.process=None
        self.error=None
        self._stop=threading.Event()
        self._monitor=None

    def start(self):
        self.process=subprocess.Popen([sys.executable,'-m','uvicorn',
            'app.modules.messaging.webhook_gateway:app','--host','127.0.0.1','--port','8788'])
        try:
            _wait_for_gateway(self.process)
        except PhotonError:
            self.stop()
            raise
        def watch():
            while not self._stop.wait(1):
                if self.process.poll() is not None:
                    self.error='Webhook receiver stopped; incoming replies are unavailable.'
                    log.error(self.error)
                    return
        self._monitor=threading.Thread(target=watch,name='photon-gateway-watch',daemon=True)
        self._monitor.start()

    def stop(self):
        self._stop.set()
        if self._monitor is not None:
            self._monitor.join(2)
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait()


def _poller(config):
    from .polling import PhotonPoller
    return PhotonPoller(config)


def _application(receiver):
    from app.main import create_app
    application=create_app()
    original=application.router.lifespan_context
    @asynccontextmanager
    async def lifespan(app):
        async with original(app):  # scenario and inbound handlers must exist before replies are dispatched
            await asyncio.to_thread(receiver.start)
            try:
                yield
            finally:
                await asyncio.to_thread(receiver.stop)
    application.router.lifespan_context=lifespan
    return application


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-party',metavar='PARTY_ID',help='Send ONE test to a configured party, then exit; no automatic retry')
    parser.add_argument('--webhook',action='store_true',help='Use signed HTTPS webhook ingress instead of local reply polling')
    args=parser.parse_args(argv)
    cfg=photon_settings()
    mappings={}
    for entry in cfg.demo_phones.split(','):
        phone,sep,party=entry.strip().rpartition(':')
        if sep and party and E164.fullmatch(phone):mappings[party]=phone
    try:
        if not mappings:raise PhotonError('Set DEMO_PHONES in backend/.env before enabling real messaging.')
        if args.test_party and args.test_party not in mappings:raise PhotonError('The requested test party is not in DEMO_PHONES.')
        if not args.test_party:
            _ports_available(webhook=args.webhook)
            if args.webhook and not(cfg.photon_webhook_secret.get_secret_value() or cfg.spectrum_webhook_secret):
                raise PhotonError('Set PHOTON_WEBHOOK_SECRET before starting the webhook receiver.')
        api=CurrentPhoton(cfg)
        if not api.agents():raise PhotonError('No available Photon Agent identity was found. Check the project line setup.')
        print('Photon project and available sending identities verified.',flush=True)
        if args.test_party:
            mid=api.send(mappings[args.test_party],'Operation Storm: authorized demo messaging test. Please reply TEST RECEIVED to confirm arrival.')
            print(f'Photon acknowledged test {mid}. Handset delivery is not yet confirmed. No automatic retry.',flush=True)
            return 0
        if not args.webhook:
            # Verify read permission without dispatching any history before the app is seeded.
            _,page=api.request('GET','/messages',params={'direction':'received','platform':cfg.photon_platform,
                'createdSince':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'pageSize':1})
            if not isinstance(page.get('items'),list):raise PhotonError('Photon reply preflight returned an invalid response.')
        os.environ['MESSAGING_MODE']='photon'
        app_settings.messaging_mode='photon'
        receiver=GatewayReceiver() if args.webhook else _poller(cfg)
        print('LIVE PHOTON MODE: approvals and claims alerts send real texts to mapped recipients.',flush=True)
        if args.webhook:
            print('Private API8000; signed webhook receiver8788. Expose only8788 through HTTPS for replies.',flush=True)
        else:
            print('Local API8000; incoming replies polled every2seconds. No tunnel is needed.',flush=True)
        print('Shared lines: each test phone must first text its assigned Photon agent number.',flush=True)
        uvicorn.run(_application(receiver),host='127.0.0.1',port=8000)
        return 0
    except PhotonError as exc:
        print(f'Live messaging did not start: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
