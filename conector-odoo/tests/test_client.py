"""Pruebas offline del cliente: perfiles, expansión de entorno y mapeo de errores."""

import xmlrpc.client

import pytest

from conector_odoo import client as client_mod
from conector_odoo.client import OdooClient, OdooError, get_profile, load_profiles

PROFILES_YML = """\
gestor:
  url: http://localhost:8169
  db: gestor
  user: ai-agent
  api_key: ${TEST_ODOO_KEY}
incompleto:
  url: http://localhost:8169
"""


@pytest.fixture
def profiles_file(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text(PROFILES_YML, encoding="utf-8")
    return str(path)


def test_load_profiles_expands_env(profiles_file, monkeypatch):
    monkeypatch.setenv("TEST_ODOO_KEY", "secret-123")
    profiles = load_profiles(profiles_file)
    assert profiles["gestor"]["api_key"] == "secret-123"
    assert profiles["gestor"]["url"] == "http://localhost:8169"


def test_load_profiles_missing_env_var(profiles_file, monkeypatch):
    monkeypatch.delenv("TEST_ODOO_KEY", raising=False)
    with pytest.raises(OdooError, match="TEST_ODOO_KEY"):
        load_profiles(profiles_file)


def test_load_profiles_via_env_location(profiles_file, monkeypatch):
    monkeypatch.setenv("TEST_ODOO_KEY", "k")
    monkeypatch.setenv("CONECTOR_ODOO_PROFILES", profiles_file)
    monkeypatch.chdir("/")
    assert "gestor" in load_profiles()


def test_get_profile_unknown(profiles_file, monkeypatch):
    monkeypatch.setenv("TEST_ODOO_KEY", "k")
    with pytest.raises(OdooError, match="no existe"):
        get_profile("nope", profiles_file)


def test_get_profile_incomplete(profiles_file, monkeypatch):
    monkeypatch.setenv("TEST_ODOO_KEY", "k")
    with pytest.raises(OdooError, match="incompleto"):
        get_profile("incompleto", profiles_file)


def _make_client():
    return OdooClient(
        {"url": "http://example.invalid", "db": "db", "user": "u", "api_key": "k"}
    )


class _FakeProxy:
    """Fake ServerProxy raising or returning canned responses."""

    def __init__(self, authenticate=1, execute_exc=None, execute_result=None):
        self._auth = authenticate
        self._exc = execute_exc
        self._result = execute_result

    def authenticate(self, *args):
        if isinstance(self._auth, Exception):
            raise self._auth
        return self._auth

    def execute_kw(self, *args):
        if self._exc:
            raise self._exc
        return self._result


def test_authenticate_caches_uid():
    cli = _make_client()
    cli._common = _FakeProxy(authenticate=7)
    assert cli.authenticate() == 7
    cli._common = _FakeProxy(authenticate=Exception("must not be called"))
    assert cli.authenticate() == 7  # cached, no second RPC


def test_authenticate_failure_message():
    cli = _make_client()
    cli._common = _FakeProxy(authenticate=False)
    with pytest.raises(OdooError, match="API key"):
        cli.authenticate()


def test_fault_maps_to_readable_error():
    cli = _make_client()
    cli._uid = 1
    fault = xmlrpc.client.Fault(1, "Traceback...\nValueError: Invalid field 'foo'")
    cli._models = _FakeProxy(execute_exc=fault)
    with pytest.raises(OdooError, match="Invalid field 'foo'"):
        cli.execute_kw("project.task", "read", [[1]])


def test_access_denied_maps_to_api_key_hint():
    cli = _make_client()
    cli._uid = 1
    fault = xmlrpc.client.Fault(3, "odoo.exceptions.AccessDenied: Access Denied")
    cli._models = _FakeProxy(execute_exc=fault)
    with pytest.raises(OdooError, match="API key inválida o expirada"):
        cli.execute_kw("project.task", "read", [[1]])


def test_connection_error_maps_to_readable_error():
    cli = _make_client()
    cli._uid = 1
    cli._models = _FakeProxy(execute_exc=ConnectionRefusedError("refused"))
    with pytest.raises(OdooError, match="No se pudo conectar"):
        cli.execute_kw("project.task", "read", [[1]])


def test_protocol_error_maps_to_readable_error():
    cli = _make_client()
    cli._uid = 1
    err = xmlrpc.client.ProtocolError("example.invalid/xmlrpc/2/object", 404, "Not Found", {})
    cli._models = _FakeProxy(execute_exc=err)
    with pytest.raises(OdooError, match="404"):
        cli.execute_kw("project.task", "read", [[1]])
