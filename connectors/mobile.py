"""iPhone (AirPlay) and Android (MTP/ADB/Cast) connectors."""
import logging
import subprocess
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── iOS / iPhone ──────────────────────────────────────────────────────────────

class AirPlayConnector:
    """
    Stream to iPhone/iPad or receive from iOS via AirPlay.
    On Windows, open-source receivers: AirServer, LonelyScreen, 5KPlayer.
    """

    def check_airserver(self) -> bool:
        """Check if AirServer (or similar) is running."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq AirServer.exe"],
                capture_output=True, text=True, timeout=3
            )
            return "AirServer.exe" in result.stdout
        except Exception:
            return False

    def check_5kplayer(self) -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq 5KPlayer.exe"],
                capture_output=True, text=True, timeout=3
            )
            return "5KPlayer.exe" in result.stdout
        except Exception:
            return False

    def launch_receiver(self) -> bool:
        """Try to launch a known AirPlay receiver app."""
        candidates = [
            r"C:\Program Files\AirServer\AirServer.exe",
            r"C:\Program Files (x86)\AirServer\AirServer.exe",
            r"C:\Program Files\5KPlayer\5KPlayer.exe",
        ]
        for path in candidates:
            try:
                subprocess.Popen([path])
                logger.info(f"Launched AirPlay receiver: {path}")
                return True
            except FileNotFoundError:
                continue
        return False

    def open_download_page(self):
        """Open browser to download an AirPlay receiver."""
        import webbrowser
        webbrowser.open("https://www.airserver.com/")

    def discover_ios_devices(self) -> List[dict]:
        """Discover iOS devices via mDNS (_airplay._tcp)."""
        try:
            from zeroconf import ServiceBrowser, Zeroconf
        except ImportError:
            return []

        devices = []
        import time

        class Listener:
            def add_service(self, zc, type_, name):
                try:
                    info = zc.get_service_info(type_, name, timeout=2000)
                    if info:
                        addrs = info.parsed_addresses()
                        devices.append({
                            "name": name.split(".")[0],
                            "address": addrs[0] if addrs else None,
                            "port": info.port,
                        })
                except Exception:
                    pass
            def remove_service(self, *_): pass
            def update_service(self, *_): pass

        zc = Zeroconf()
        ServiceBrowser(zc, "_airplay._tcp.local.", Listener())
        time.sleep(3)
        zc.close()
        return devices


# ── Android ────────────────────────────────────────────────────────────────────

class AndroidConnector:
    """
    Android connection via:
    - ADB (USB debugging) for file transfer and screen mirror
    - scrcpy for screen mirroring
    - Miracast (wireless display - handled by miracast.py)
    """

    def is_adb_available(self) -> bool:
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, timeout=3)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def list_adb_devices(self) -> List[dict]:
        """List connected Android devices via ADB."""
        if not self.is_adb_available():
            return []
        try:
            result = subprocess.run(["adb", "devices", "-l"],
                                    capture_output=True, text=True, timeout=5)
            devices = []
            for line in result.stdout.splitlines()[1:]:
                line = line.strip()
                if not line or "offline" in line:
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    model = next((p.replace("model:", "") for p in parts if p.startswith("model:")), "Android")
                    devices.append({"serial": parts[0], "model": model})
            return devices
        except Exception as e:
            logger.error(f"ADB list error: {e}")
            return []

    def connect_adb_wireless(self, ip: str, port: int = 5555) -> bool:
        """Connect to Android device over WiFi via ADB."""
        if not self.is_adb_available():
            logger.warning("ADB not found in PATH")
            return False
        try:
            result = subprocess.run(["adb", "connect", f"{ip}:{port}"],
                                    capture_output=True, text=True, timeout=10)
            success = "connected" in result.stdout.lower()
            if success:
                logger.info(f"ADB connected: {ip}:{port}")
            return success
        except Exception as e:
            logger.error(f"ADB connect error: {e}")
            return False

    def mirror_screen(self, serial: Optional[str] = None) -> bool:
        """Mirror Android screen via scrcpy (must be installed)."""
        cmd = ["scrcpy"]
        if serial:
            cmd += ["-s", serial]
        try:
            subprocess.Popen(cmd)
            return True
        except FileNotFoundError:
            logger.warning("scrcpy not found — download from https://github.com/Genymobile/scrcpy")
            return False

    def is_scrcpy_available(self) -> bool:
        try:
            subprocess.run(["scrcpy", "--version"], capture_output=True, timeout=3)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def open_scrcpy_download(self):
        import webbrowser
        webbrowser.open("https://github.com/Genymobile/scrcpy/releases")

    def enable_wifi_adb(self, serial: str, port: int = 5555) -> bool:
        """Enable TCP/IP ADB on a USB-connected device, then disconnect USB."""
        if not self.is_adb_available():
            return False
        try:
            subprocess.run(["adb", "-s", serial, "tcpip", str(port)], timeout=5)
            result = subprocess.run(["adb", "-s", serial, "shell", "ip", "route"],
                                    capture_output=True, text=True, timeout=5)
            logger.info(f"WiFi ADB enabled on port {port}")
            return True
        except Exception as e:
            logger.error(f"Enable WiFi ADB error: {e}")
            return False
