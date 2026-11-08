"""Read-only readiness: python -m app.modules.messaging.check_photon [--live]."""
import argparse
import json
from .current_api import CurrentPhoton
from .photon import PhotonError, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Read-only project and sender verification; never sends')
    args = parser.parse_args()
    cfg = settings()
    recipients = {e.strip().rpartition(':')[0] for e in cfg.demo_phones.split(',') if ':' in e}
    result = {'api_key_configured': bool(cfg.photon_api_key.get_secret_value()),
        'project_id_configured': bool(cfg.photon_project_id),
        'webhook_secret_configured': bool(cfg.photon_webhook_secret.get_secret_value() or cfg.spectrum_webhook_secret),
        'recipient_count': len(recipients),
        'claims_recipient_allowed': bool(cfg.photon_claims_alert_phone and cfg.photon_claims_alert_phone in recipients),
        'live_verified': False}
    success = result['api_key_configured'] and result['project_id_configured'] and result['recipient_count'] > 0
    if args.live:
        try:
            client = CurrentPhoton(cfg)
            client.request('GET', '')
            result['sender_id'] = client.sender()
            result['live_verified'] = True
        except PhotonError as exc:
            result['error'] = str(exc)
            success = False
    print(json.dumps(result, indent=2))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
