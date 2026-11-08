"""Local live messaging. Run from backend/: python -m app.modules.messaging.live.
Add --test-party MGR-01 to send one explicit test and exit instead of starting services.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys

import uvicorn

from app.shared.config import settings as app_settings
from .current_api import CurrentPhoton, E164
from .photon import PhotonError, settings as photon_settings


def _ports_available():
    for port in (8000, 8788):
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise PhotonError(f'Port {port} is already in use. Stop the existing local service before starting live messaging.') from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-party', metavar='PARTY_ID', help='Send ONE test to a configured party, then exit; never retried automatically')
    args = parser.parse_args(argv)
    cfg = photon_settings()
    mappings = {}
    for entry in cfg.demo_phones.split(','):
        phone, sep, party = entry.strip().rpartition(':')
        if sep and party and E164.fullmatch(phone):
            mappings[party] = phone
    try:
        if not mappings:
            raise PhotonError('Set DEMO_PHONES in backend/.env before enabling real messaging.')
        if args.test_party and args.test_party not in mappings:
            raise PhotonError('The requested test party is not in DEMO_PHONES.')
        if not args.test_party:
            _ports_available()
            if not (cfg.photon_webhook_secret.get_secret_value() or cfg.spectrum_webhook_secret):
                raise PhotonError('Set PHOTON_WEBHOOK_SECRET in backend/.env before starting the live receiver.')
        api = CurrentPhoton(cfg)
        api.request('GET', '')
        sender = api.sender()
        cfg.photon_sender_id = sender
        print('Photon project and dedicated sending identity verified.', flush=True)
        if args.test_party:
            message_id = api.send(mappings[args.test_party], 'Operation Storm: authorized demo messaging test. Please reply TEST RECEIVED to confirm this message arrived.')
            print(f'Photon acknowledged test {message_id}. Handset delivery is not yet confirmed. No automatic retry.', flush=True)
            return 0
        os.environ['MESSAGING_MODE'] = 'photon'
        app_settings.messaging_mode = 'photon'
        # Child and API share the same private .env; no secret is put in process arguments.
        gateway = subprocess.Popen([sys.executable, '-m', 'uvicorn',
            'app.modules.messaging.webhook_gateway:app', '--host', '127.0.0.1', '--port', '8788'])
        try:
            print('LIVE PHOTON MODE: approvals and claims alerts send real texts to mapped recipients.', flush=True)
            print('Private API: port8000. Webhook-only receiver: port8788. Expose only8788 through your HTTPS tunnel.', flush=True)
            print('Register https://<tunnel-host>/api/webhooks/photon in the Photon webhook destination for replies.', flush=True)
            uvicorn.run('app.main:app', host='127.0.0.1', port=8000)
        finally:
            if gateway.poll() is None:
                gateway.terminate()
                try:
                    gateway.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    gateway.kill(); gateway.wait()
        return 0
    except PhotonError as exc:
        print(f'Live messaging did not start: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
