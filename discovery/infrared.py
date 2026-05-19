"""Infrared control — requires hardware IR blaster (e.g. USB-UIRT, LIRC, Irdroid)."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Common IR codes (NEC protocol, common TV brands)
IR_CODES = {
    "samsung": {
        "power": "0xE0E040BF",
        "volume_up": "0xE0E0E01F",
        "volume_down": "0xE0E0D02F",
        "mute": "0xE0E0F00F",
        "hdmi1": "0xE0E09768",
        "hdmi2": "0xE0E07D82",
    },
    "lg": {
        "power": "0x20DF10EF",
        "volume_up": "0x20DF40BF",
        "volume_down": "0x20DFC03F",
        "mute": "0x20DF906F",
        "hdmi1": "0x20DFA15E",
        "hdmi2": "0x20DF619E",
    },
    "sony": {
        "power": "0xA90",
        "volume_up": "0x490",
        "volume_down": "0xC90",
        "mute": "0x290",
    },
    "philips": {
        "power": "0x170C",
        "volume_up": "0x1700",
        "volume_down": "0x1701",
        "mute": "0x170D",
    },
}


class IRController:
    """Abstract IR controller — implement send_code() for your hardware."""

    def __init__(self):
        self._backend = self._detect_backend()

    def _detect_backend(self) -> Optional[str]:
        # Try USB-UIRT
        try:
            import usbuirt
            return "usbuirt"
        except ImportError:
            pass
        # Try LIRC (Linux/Raspberry Pi mostly, but some Windows support)
        try:
            import lirc
            return "lirc"
        except ImportError:
            pass
        # Try WinLIRC
        try:
            import socket
            s = socket.socket()
            s.settimeout(1)
            s.connect(("127.0.0.1", 8765))
            s.close()
            return "winlirc"
        except Exception:
            pass
        return None

    @property
    def available(self) -> bool:
        return self._backend is not None

    def send_code(self, brand: str, command: str) -> bool:
        """Send an IR command. Returns True if sent."""
        codes = IR_CODES.get(brand.lower(), {})
        code = codes.get(command)
        if not code:
            logger.warning(f"No IR code for {brand}/{command}")
            return False

        if not self._backend:
            logger.warning("No IR hardware backend detected")
            return False

        if self._backend == "winlirc":
            return self._send_winlirc(brand, command)
        if self._backend == "usbuirt":
            return self._send_usbuirt(code)
        return False

    def _send_winlirc(self, remote: str, command: str) -> bool:
        import socket
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect(("127.0.0.1", 8765))
            s.sendall(f"SEND_ONCE {remote} {command}\n".encode())
            s.close()
            return True
        except Exception as e:
            logger.error(f"WinLIRC send error: {e}")
            return False

    def _send_usbuirt(self, code: str) -> bool:
        try:
            import usbuirt
            device = usbuirt.open()
            usbuirt.transmit(device, code)
            return True
        except Exception as e:
            logger.error(f"USB-UIRT send error: {e}")
            return False

    def power_toggle(self, brand: str) -> bool:
        return self.send_code(brand, "power")

    def volume_up(self, brand: str) -> bool:
        return self.send_code(brand, "volume_up")

    def volume_down(self, brand: str) -> bool:
        return self.send_code(brand, "volume_down")

    def switch_hdmi(self, brand: str, input_num: int = 1) -> bool:
        return self.send_code(brand, f"hdmi{input_num}")


# Singleton
_controller: Optional[IRController] = None


def get_ir_controller() -> IRController:
    global _controller
    if _controller is None:
        _controller = IRController()
    return _controller
