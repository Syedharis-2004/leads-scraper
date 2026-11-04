"""
Secure API-key storage.

Primary backend: Windows Credential Manager via the *keyring* package.
Fallback: DPAPI-style encrypted file (Windows) or plain file on other OS.

The API key is never returned in full by any function in this module;
callers receive a boolean "has key" status and use ``get_api_key()``
internally only when they need to make an API call.
"""

import json
import os
from typing import Optional

from config.settings import APP_CONFIG_PATH, KEYRING_SERVICE, KEYRING_USERNAME, ensure_dirs
from utils.logging_config import logger

try:
    import keyring
    import keyring.errors

    _KEYRING_AVAILABLE = True
except Exception:  # pragma: no cover - keyring should be installed
    _KEYRING_AVAILABLE = False
    logger.warning("keyring package not available; falling back to file storage")

# Fallback file (only used when keyring is unavailable)
_FALLBACK_FILE = APP_CONFIG_PATH.parent / ".api_key_store.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def has_api_key() -> bool:
    """Return True if an API key is currently stored."""
    key = get_api_key()
    return bool(key)


def save_api_key(api_key: str) -> None:
    """Persist the Gemini API key securely."""
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API key cannot be empty")
    if _KEYRING_AVAILABLE:
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            logger.info("API key saved to Windows Credential Manager")
            return
        except Exception as exc:
            logger.warning(f"keyring save failed ({exc}); using fallback file")
    _save_fallback(api_key)


def get_api_key() -> Optional[str]:
    """Retrieve the stored API key, or None if not set."""
    if _KEYRING_AVAILABLE:
        try:
            key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if key:
                return key
        except Exception as exc:
            logger.warning(f"keyring read failed ({exc})")
    return _load_fallback()


def update_api_key(api_key: str) -> None:
    """Replace the stored API key."""
    save_api_key(api_key)


def remove_api_key() -> bool:
    """Delete the stored API key.  Returns True if a key was removed."""
    removed = False
    if _KEYRING_AVAILABLE:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            removed = True
        except keyring.errors.PasswordDeleteError:
            pass  # nothing to delete
        except Exception as exc:
            logger.warning(f"keyring delete failed ({exc})")
    if _fallback_exists():
        _delete_fallback()
        removed = True
    logger.info("API key removed" if removed else "No API key to remove")
    return removed


# ---------------------------------------------------------------------------
# Fallback file storage (DPAPI on Windows, plain on others)
# ---------------------------------------------------------------------------

def _fallback_exists() -> bool:
    return _FALLBACK_FILE.exists()


def _save_fallback(api_key: str) -> None:
    ensure_dirs()
    # On Windows we can use DPAPI via ctypes for per-user encryption.
    encrypted = _dpapi_encrypt(api_key)
    _FALLBACK_FILE.write_text(json.dumps({"k": encrypted}), encoding="utf-8")


def _load_fallback() -> Optional[str]:
    if not _fallback_exists():
        return None
    try:
        data = json.loads(_FALLBACK_FILE.read_text(encoding="utf-8"))
        return _dpapi_decrypt(data.get("k", ""))
    except Exception:
        return None


def _delete_fallback() -> None:
    try:
        _FALLBACK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _dpapi_encrypt(plaintext: str) -> str:
    """Encrypt *plaintext* using Windows DPAPI (CryptProtectData)."""
    if os.name != "nt":
        # Non-Windows: store base64 (fallback only; keyring should be used)
        import base64
        return "plain:" + base64.b64encode(plaintext.encode()).decode()

    import base64
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                     ("pbData", ctypes.POINTER(ctypes.c_char))]

    data = plaintext.encode("utf-8")
    src = DATA_BLOB(len(data), ctypes.cast(
        ctypes.create_string_buffer(data, len(data)),
        ctypes.POINTER(ctypes.c_char)))
    dst = DATA_BLOB()

    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)
    ):
        raise OSError("CryptProtectData failed")

    try:
        encrypted = ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(dst.pbData)

    return "dpapi:" + base64.b64encode(encrypted).decode()


def _dpapi_decrypt(ciphertext: str) -> Optional[str]:
    """Decrypt data produced by :func:`_dpapi_encrypt`."""
    if not ciphertext:
        return None

    if ciphertext.startswith("plain:"):
        import base64
        return base64.b64decode(ciphertext[6:]).decode("utf-8")

    if ciphertext.startswith("dpapi:"):
        import base64
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                         ("pbData", ctypes.POINTER(ctypes.c_char))]

        raw = base64.b64decode(ciphertext[6:])
        src = DATA_BLOB(len(raw), ctypes.cast(
            ctypes.create_string_buffer(raw, len(raw)),
            ctypes.POINTER(ctypes.c_char)))
        dst = DATA_BLOB()

        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)
        ):
            raise OSError("CryptUnprotectData failed")

        try:
            plaintext = ctypes.string_at(dst.pbData, dst.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(dst.pbData)

        return plaintext.decode("utf-8")

    return None
