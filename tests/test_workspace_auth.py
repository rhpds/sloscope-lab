"""Execute the actual devfile bootstrap with synthetic credentials and no network."""
import io
import json
import os
from pathlib import Path
import ssl
import stat
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import HTTPSHandler

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def bootstrap():
    devfile = yaml.safe_load((ROOT / '.devfile.yaml').read_text())
    command = next(c['exec']['commandLine'] for c in devfile['commands'] if c['id'] == 'setup-workspace')
    assert command.startswith("python3 - <<'PY'\n") and command.endswith('PY\n')
    scope = {'__name__': 'workspace_auth_test'}
    exec(compile(command.split('\n', 1)[1].rsplit('\nPY', 1)[0], '.devfile.yaml:setup-workspace', 'exec'), scope)
    return scope


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('PH_CA_BUNDLE', raising=False)
    original = Path.read_text
    def read(path, *args, **kwargs):
        if str(path) == '/var/run/secrets/kubernetes.io/serviceaccount/token':
            return 'synthetic-workspace-token'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read)
    return bootstrap(), tmp_path / '.config' / 'publishing-house'


def fake_opener(scope, monkeypatch, replies):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert timeout == 30
            value = replies[len(calls)-1]
            if isinstance(value, Exception):
                raise value
            return io.BytesIO(json.dumps(value).encode())
    def build(*handlers):
        tls = next(h for h in handlers if isinstance(h, HTTPSHandler))._context
        assert tls.verify_mode == ssl.CERT_REQUIRED and tls.check_hostname is True
        assert any(isinstance(h, scope['NoRedirect']) for h in handlers)
        return Opener()
    monkeypatch.setitem(scope, 'build_opener', build)
    return calls


def test_verified_bootstrap_installs_private_atomic_config_even_with_permissive_umask(setup, monkeypatch, capsys):
    scope, directory = setup
    calls = fake_opener(scope, monkeypatch, [
        {'api_key': 'synthetic-ph-key'},
        {'litellm_key': 'synthetic-model-key', 'litellm_endpoint': 'https://model.example/v1', 'litellm_model': 'test-model'},
    ])
    before = os.umask(0)
    try:
        scope['setup']()
    finally:
        os.umask(before)
    path = directory / 'auth.json'
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(directory.iterdir()) == [path]
    assert json.loads(path.read_text())['litellm_key'] == 'synthetic-model-key'
    assert [r.get_header('Authorization') for r in calls] == [
        'Bearer synthetic-workspace-token', 'Bearer synthetic-ph-key']
    assert json.loads(calls[1].data) == {'project_id': 'sloscope-lab'}
    output = capsys.readouterr()
    assert output.out.strip() == 'Workspace auth configured' and not output.err
    assert 'synthetic-' not in output.out


@pytest.mark.parametrize('error', [ssl.SSLCertVerificationError('synthetic-secret-in-error'),
    HTTPError('https://ph.example', 401, 'synthetic-secret-in-error', {}, None)])
def test_tls_and_http_failures_leave_no_auth_file(setup, monkeypatch, error):
    scope, directory = setup
    fake_opener(scope, monkeypatch, [error])
    with pytest.raises(type(error)):
        scope['setup']()
    assert not (directory / 'auth.json').exists()
    assert list(directory.iterdir()) == []


def test_partial_response_does_not_replace_existing_config(setup, monkeypatch):
    scope, directory = setup
    directory.mkdir(parents=True)
    path = directory / 'auth.json'
    original = '{"credential":"synthetic-old-key"}'
    path.write_text(original)
    fake_opener(scope, monkeypatch, [{'api_key': 'synthetic-new-key'}, {'litellm_key': 'incomplete'}])
    with pytest.raises(ValueError, match='Incomplete model configuration'):
        scope['setup']()
    assert path.read_text() == original
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_existing_config_permissions_repaired_without_network_or_token_read(setup, monkeypatch):
    scope, directory = setup
    directory.mkdir(parents=True)
    directory.chmod(0o755)
    path = directory / 'auth.json'
    path.write_text(json.dumps({k: 'test-only' for k in ('credential', 'litellm_key', 'litellm_endpoint', 'litellm_model')}))
    path.chmod(0o644)
    monkeypatch.setitem(scope, 'build_opener', lambda *args: pytest.fail('already configured auth contacted PH'))
    scope['setup']()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_redirects_and_symlink_destinations_are_rejected(setup):
    scope, directory = setup
    assert scope['NoRedirect']().redirect_request(None, None, 302, '', {}, 'https://other.example') is None
    other = directory.parent / 'other'
    other.mkdir(parents=True)
    directory.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match='symbolic links'):
        scope['setup']()


def test_explicit_enterprise_ca_bundle_is_used(setup, monkeypatch):
    scope, _ = setup
    monkeypatch.setenv('PH_CA_BUNDLE', '/synthetic/enterprise-ca.pem')
    seen = []
    real = ssl.create_default_context
    def context(*, cafile):
        seen.append(cafile)
        return real()
    monkeypatch.setattr(ssl, 'create_default_context', context)
    fake_opener(scope, monkeypatch, [{'api_key': 'test-only'},
        {'litellm_key': 'test-only', 'litellm_endpoint': 'https://model.example', 'litellm_model': 'test-only'}])
    scope['setup']()
    assert seen == ['/synthetic/enterprise-ca.pem']


def test_bootstrap_entrypoint_fails_closed_without_logging_exception_details(tmp_path):
    devfile = yaml.safe_load((ROOT / '.devfile.yaml').read_text())
    command = next(c['exec']['commandLine'] for c in devfile['commands'] if c['id'] == 'setup-workspace')
    code = command.split('\n', 1)[1].rsplit('\nPY', 1)[0]
    env = dict(os.environ, HOME=str(tmp_path), PH_CA_BUNDLE=str(tmp_path/'synthetic-secret-missing-ca.pem'))
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert not result.stdout
    assert 'Workspace auth setup failed' in result.stderr
    assert 'synthetic-secret' not in result.stderr and 'Traceback' not in result.stderr
    assert not (tmp_path/'.config/publishing-house/auth.json').exists()
