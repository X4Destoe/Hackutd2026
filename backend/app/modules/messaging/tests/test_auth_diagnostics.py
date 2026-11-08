import json
from app.modules.messaging import check_photon, photon
from app.modules.messaging.current_api import PhotonAPIError


def test_safe_diagnostics_find_shell_override_without_disclosing_keys(tmp_path,monkeypatch):
    p=tmp_path/'.env';p.write_text('PHOTON_API_KEY=pho_sk_file-private-value\nPHOTON_PROJECT_ID=pho_prj_test\n',encoding='utf-8')
    monkeypatch.setenv('PHOTON_API_KEY','pho_sk_shell-private-value')
    monkeypatch.setenv('PHOTON_PROJECT_ID','pho_prj_test')
    cfg=photon.PhotonSettings(_env_file=None,photon_api_key='pho_sk_shell-private-value',photon_project_id='pho_prj_test')
    result=check_photon.credential_diagnostics(cfg,p)
    assert result['api_key_kind']=='project' and result['shell_key_differs_from_file']
    assert not result['shell_project_differs_from_file']
    assert 'private-value' not in json.dumps(result)


def test_placeholder_and_wrong_credential_type_are_identified(tmp_path,monkeypatch):
    monkeypatch.delenv('PHOTON_API_KEY',raising=False)
    p=tmp_path/'.env'
    cfg=photon.PhotonSettings(_env_file=None,photon_api_key='your_actual_photon_key')
    assert check_photon.credential_diagnostics(cfg,p)['api_key_is_placeholder']
    cfg.photon_api_key=photon.SecretStr('whsec_not-an-api-key')
    result=check_photon.credential_diagnostics(cfg,p)
    assert result['api_key_kind']=='webhook-secret-not-api-key'
    assert not result['config_file_exists']
    assert 'whsec_not-an-api-key' not in json.dumps(result)


def test_blank_shell_value_is_detected_as_override(tmp_path,monkeypatch):
    p=tmp_path/'.env';p.write_text('PHOTON_API_KEY=pho_sk_file-private-value\n',encoding='utf-8')
    monkeypatch.setenv('PHOTON_API_KEY','')
    cfg=photon.PhotonSettings(_env_file=None,photon_api_key='')
    result=check_photon.credential_diagnostics(cfg,p)
    assert result['api_key_set_in_shell'] and result['shell_key_differs_from_file']


def test_401_guidance_contains_no_credential_or_provider_error_body():
    error=PhotonAPIError(401)
    assert error.status==401 and 'PHOTON_API_KEY' in str(error) and 'shell override' in str(error)
