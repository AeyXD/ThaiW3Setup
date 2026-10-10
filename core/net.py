"""HTTPS requests that also verify on the macOS build.

The .app bundles python.org's Python, and its OpenSSL trusts no certificate authority until the installer's
"Install Certificates" step runs, which never happens inside a bundle. Every request then failed with
CERTIFICATE_VERIFY_FAILED, so the Mac build checked for updates, downloaded the sheets and sent reports in
vain, falling back to the translations frozen into the release. certifi's bundle fixes that; Windows keeps
reading its own certificate store.
"""
from __future__ import annotations

import functools
import logging
import ssl
import urllib.request

from .osutil import WINDOWS

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not WINDOWS:
        try:
            import certifi
            ctx.load_verify_locations(cafile=certifi.where())
        except (ImportError, OSError) as exc:  # still try what the system trusts
            log.warning("certifi unavailable, using the default certificate store: %s", exc)
    return ctx


def urlopen(req: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())


def is_certificate_error(exc: BaseException) -> bool:
    """True when the connection worked but the server's certificate could not be verified."""
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
