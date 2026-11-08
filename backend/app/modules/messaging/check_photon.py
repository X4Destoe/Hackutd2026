"""Read-only readiness: python -m app.modules.messaging.check_photon [--live]."""
import argparse
import json
import os
from pathlib import Path
from dotenv import dotenv_values
from app.shared.config import BACKEND_DIR
from .current_api import CurrentPhoton
from .photon import PhotonError, settings


def credential_diagnostics(config, path=None):
    path = Path(path) if path is not None else BACKEND_DIR / '.env'
    values = dotenv_values(path) if path.is_file() else {}
    key = config.photon_api_key.get_secret_value()
    kind = ('project' if key.startswith('pho_sk_') else 'account' if key.startswith('pho_ask_')
            else 'webhook-secret-not-api-key' if key.startswith('whsec_') else 'unrecognized-or-missing')
    shell_has_key = 'PHOTON_API_KEY' in os.environ
    shell_has_project = 'PHOTON_PROJECT_ID' in os.environ
    return {
        'config_file': str(path),
        'config_file_exists': path.is_file(),
        'api_key_kind': kind,
        'api_key_has_whitespace': any(c.isspace() for c in key),
        'api_key_is_placeholder': key.lower() in {'your_actual_photon_key', 'your_photon_api_key', 'your_key', 'paste_key_here'},
        'api_key_set_in_shell': shell_has_key,
        'shell_key_differs_from_file': shell_has_key and os.environ.get('PHOTON_API_KEY') != values.get('PHOTON_API_KEY'),
        'shell_project_differs_from_file': shell_has_project and os.environ.get('PHOTON_PROJECT_ID') != values.get('PHOTON_PROJECT_ID'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Read-only project and sender verification; never sends')
    args = parser.parse_args()
    cfg = settings()
    recipients = {e.strip().rpartition(':')[0] for e in cfg.demo_phones.split(',') if ':' in e}
    result = {**credential_diagnostics(cfg), 'api_key_configured': bool(cfg.photon_api_key.get_secret_value()),
        'project_id_configured': bool(cfg.photon_project_id),
        'webhook_secret_configured': bool(cfg.photon_webhook_secret.get_secret_value() or cfg.spectrum_webhook_secret),
        'recipient_count': len(recipients),
        'claims_recipient_allowed': bool(cfg.photon_claims_alert_phone and cfg.photon_claims_alert_phone in recipients),
        'live_verified': False}
    success = result['api_key_configured'] and result['project_id_configured'] and result['recipient_count'] > 0
    if args.live:
        try:
            client = CurrentPhoton(cfg)
            agents = client.agents()
            if not agents:
                raise PhotonError('No available Photon Agent identity was found. Check the project line setup.')
            result['sender_ids'] = list(agents)
            result['live_verified'] = True
        except PhotonError as exc:
            result['error'] = str(exc)
            success = False
    print(json.dumps(result, indent=2))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
