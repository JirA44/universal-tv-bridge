"""Windows Miracast/WiDi wireless display connector."""
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def open_connect_ui():
    """Open Windows 'Connect' panel (Project/Wireless display)."""
    try:
        subprocess.Popen(["ms-settings-connectabledevices:"])
        return True
    except Exception:
        pass
    try:
        subprocess.Popen(["start", "ms-settings:display-connectwirelessprojection"], shell=True)
        return True
    except Exception as e:
        logger.error(f"Cannot open Connect UI: {e}")
        return False


def open_projection_ui():
    """Open Windows projection mode selector (Duplicate/Extend/Second screen only)."""
    try:
        subprocess.Popen(["displayswitch.exe", "/extend"])
        return True
    except Exception as e:
        logger.error(f"Cannot open projection UI: {e}")
        return False


def set_display_mode(mode: str = "extend") -> bool:
    """
    mode: 'internal', 'clone', 'extend', 'external'
    Uses displayswitch.exe — takes effect immediately.
    """
    mode_map = {
        "internal": "/internal",
        "clone": "/clone",
        "duplicate": "/clone",
        "extend": "/extend",
        "external": "/external",
    }
    flag = mode_map.get(mode.lower())
    if not flag:
        logger.error(f"Unknown display mode: {mode}")
        return False
    try:
        subprocess.run(["displayswitch.exe", flag], check=True)
        return True
    except Exception as e:
        logger.error(f"displayswitch error: {e}")
        return False


def connect_miracast_device(device_name: Optional[str] = None) -> bool:
    """
    Opens Windows Connect app which auto-discovers Miracast receivers.
    If device_name is provided, logs it for user context.
    """
    if device_name:
        logger.info(f"Connecting to Miracast device: {device_name}")
    return open_connect_ui()
