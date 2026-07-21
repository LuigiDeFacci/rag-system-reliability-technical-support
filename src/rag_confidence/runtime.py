"""Runtime compatibility helpers that do not alter experiment semantics."""

from __future__ import annotations

import sys


def configure_system_trust_store() -> None:
    """Use the Windows certificate store for HTTPS clients on older Python installs."""
    if sys.platform != "win32":
        return
    try:
        import truststore
    except ImportError as error:
        raise RuntimeError(
            "Windows HTTPS requires the declared 'truststore' dependency in this environment."
        ) from error
    truststore.inject_into_ssl()
