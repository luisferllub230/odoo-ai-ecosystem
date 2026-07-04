"""Cliente Odoo XML-RPC con configuración por perfiles (profiles.yml)."""

import os
import re
import socket
import xmlrpc.client
from pathlib import Path

import yaml

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Search order for profiles.yml: explicit arg, env var, cwd, package repo root.
_DEFAULT_LOCATIONS = (
    lambda: os.environ.get("CONECTOR_ODOO_PROFILES"),
    lambda: Path.cwd() / "profiles.yml",
    lambda: Path(__file__).resolve().parents[2] / "profiles.yml",
)


class OdooError(Exception):
    """Error de conexión o de la API de Odoo con mensaje legible."""


def _expand_env(value):
    """Recursively expand ${VAR} references from the environment."""
    if isinstance(value, str):
        def repl(match):
            var = match.group(1)
            if var not in os.environ:
                raise OdooError(
                    f"Variable de entorno '{var}' no definida (requerida por profiles.yml)"
                )
            return os.environ[var]

        return _ENV_VAR_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_profiles(path=None):
    """Carga profiles.yml y expande secretos ${VAR} desde el entorno."""
    candidates = [path] if path else [loc() for loc in _DEFAULT_LOCATIONS]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            with open(candidate, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return _expand_env(data)
    raise OdooError(
        "No se encontró profiles.yml (defina CONECTOR_ODOO_PROFILES o ejecute desde conector-odoo/)"
    )


def get_profile(name, path=None):
    """Devuelve la configuración de un perfil por nombre."""
    profiles = load_profiles(path)
    if name not in profiles:
        raise OdooError(
            f"Perfil '{name}' no existe. Perfiles disponibles: {', '.join(sorted(profiles))}"
        )
    profile = profiles[name]
    missing = [k for k in ("url", "db", "user", "api_key") if not profile.get(k)]
    if missing:
        raise OdooError(f"Perfil '{name}' incompleto, faltan campos: {', '.join(missing)}")
    return profile


def _map_error(exc, context):
    """Map raw transport/Odoo exceptions to a readable OdooError."""
    if isinstance(exc, xmlrpc.client.Fault):
        # Odoo puts the traceback in faultString; keep only the last meaningful line.
        fault = (exc.faultString or "").strip()
        lines = [ln for ln in fault.splitlines() if ln.strip()]
        detail = lines[-1] if lines else f"fault {exc.faultCode}"
        if "AccessDenied" in fault or "Access Denied" in fault:
            detail = "acceso denegado: API key inválida o expirada, o usuario incorrecto"
        elif "AccessError" in fault:
            detail = f"permisos insuficientes para la operación ({detail})"
        return OdooError(f"Error de Odoo en {context}: {detail}")
    if isinstance(exc, xmlrpc.client.ProtocolError):
        return OdooError(
            f"Error HTTP {exc.errcode} contra {exc.url} en {context}: {exc.errmsg}"
        )
    if isinstance(exc, (ConnectionError, socket.error, OSError)):
        return OdooError(f"No se pudo conectar al servidor Odoo en {context}: {exc}")
    return OdooError(f"Error inesperado en {context}: {exc}")


class OdooClient:
    """Cliente XML-RPC mínimo: autentica una vez y envuelve execute_kw."""

    def __init__(self, profile):
        self.url = profile["url"].rstrip("/")
        self.db = profile["db"]
        self.user = profile["user"]
        self.api_key = profile["api_key"]
        self._uid = None
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    @classmethod
    def from_profile(cls, name, path=None):
        """Crea un cliente a partir del nombre de un perfil."""
        return cls(get_profile(name, path))

    def authenticate(self):
        """Autentica contra /xmlrpc/2/common y cachea el uid."""
        if self._uid is not None:
            return self._uid
        try:
            uid = self._common.authenticate(self.db, self.user, self.api_key, {})
        except Exception as exc:  # noqa: BLE001 - mapped to readable error
            raise _map_error(exc, f"authenticate({self.db})") from exc
        if not uid:
            raise OdooError(
                f"Autenticación fallida en {self.url} (db='{self.db}', user='{self.user}'): "
                "verifique que la base de datos exista y que la API key sea válida y no haya expirado"
            )
        self._uid = uid
        return uid

    def execute_kw(self, model, method, args, kwargs=None):
        """Ejecuta model.method(*args, **kwargs) vía /xmlrpc/2/object."""
        uid = self.authenticate()
        try:
            return self._models.execute_kw(
                self.db, uid, self.api_key, model, method, args, kwargs or {}
            )
        except Exception as exc:  # noqa: BLE001 - mapped to readable error
            raise _map_error(exc, f"{model}.{method}") from exc
