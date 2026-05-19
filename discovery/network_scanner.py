"""WiFi/mDNS/SSDP/UPnP device discovery."""
import asyncio
import logging
import socket
import struct
import threading
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

from .models import Device, DeviceType, Protocol

logger = logging.getLogger(__name__)

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3
SSDP_TARGETS = [
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:device:MediaRenderer:2",
    "urn:schemas-upnp-org:device:MediaServer:1",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:schemas-upnp-org:device:Basic:1",
    "ssdp:all",
]

CHROMECAST_PORTS = [8009]
AIRPLAY_SERVICE = "_airplay._tcp.local."
DLNA_SERVICE = "_dlna._udp.local."


def _ssdp_request(target: str) -> bytes:
    msg = (
        f"M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        f"MAN: \"ssdp:discover\"\r\n"
        f"MX: {SSDP_MX}\r\n"
        f"ST: {target}\r\n"
        f"\r\n"
    )
    return msg.encode()


def _fetch_device_description(location: str) -> Optional[Dict]:
    try:
        resp = requests.get(location, timeout=3)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"u": "urn:schemas-upnp-org:device-1-0"}
        device_el = root.find(".//u:device", ns)
        if device_el is None:
            device_el = root.find(".//{urn:schemas-upnp-org:device-1-0}device")
        if device_el is None:
            return None

        def get(tag):
            el = device_el.find(f"{{urn:schemas-upnp-org:device-1-0}}{tag}")
            return el.text.strip() if el is not None and el.text else None

        return {
            "friendly_name": get("friendlyName"),
            "manufacturer": get("manufacturer"),
            "model": get("modelName"),
            "device_type": get("deviceType"),
        }
    except Exception as e:
        logger.debug(f"Failed to fetch device description from {location}: {e}")
        return None


def _classify_upnp_device(info: Dict) -> DeviceType:
    dt = (info.get("device_type") or "").lower()
    name = (info.get("friendly_name") or "").lower()
    manufacturer = (info.get("manufacturer") or "").lower()
    text = f"{dt} {name} {manufacturer}"

    if "mediarenderer" in dt:
        return DeviceType.TV
    if any(k in text for k in ("samsung", "lg", "sony", "bravia", "philips", "tcl", "hisense")):
        return DeviceType.TV
    if any(k in text for k in ("freebox", "livebox", "bbox", "sfr", "orange")):
        return DeviceType.BOX
    if any(k in text for k in ("playstation", "xbox", "nintendo")):
        return DeviceType.CONSOLE
    return DeviceType.UNKNOWN


def scan_ssdp(timeout: float = 5.0,
              on_device: Callable[[Device], None] = None) -> List[Device]:
    devices: List[Device] = []
    seen_locations: set = set()
    seen_addresses: set = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
    sock.settimeout(timeout)

    try:
        for target in SSDP_TARGETS:
            try:
                sock.sendto(_ssdp_request(target), (SSDP_ADDR, SSDP_PORT))
            except Exception:
                pass

        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
                response = data.decode("utf-8", errors="ignore")
                headers = {}
                for line in response.split("\r\n")[1:]:
                    if ":" in line:
                        key, _, val = line.partition(":")
                        headers[key.strip().upper()] = val.strip()

                location = headers.get("LOCATION", "")
                if not location or location in seen_locations:
                    continue
                seen_locations.add(location)

                parsed = urlparse(location)
                ip = parsed.hostname or addr[0]
                port = parsed.port

                if ip in seen_addresses:
                    continue
                seen_addresses.add(ip)

                info = _fetch_device_description(location) or {}
                name = info.get("friendly_name") or headers.get("SERVER", f"Device {ip}")
                device_type = _classify_upnp_device(info)

                protocol = Protocol.CHROMECAST if port in CHROMECAST_PORTS else Protocol.DLNA

                device = Device(
                    id=f"upnp_{ip}",
                    name=name,
                    device_type=device_type,
                    protocol=protocol,
                    address=ip,
                    port=port,
                    model=info.get("model"),
                    manufacturer=info.get("manufacturer"),
                    extra={"location": location, "server": headers.get("SERVER", "")},
                )
                devices.append(device)
                if on_device:
                    on_device(device)

            except socket.timeout:
                break
            except Exception as e:
                logger.debug(f"SSDP recv error: {e}")
    finally:
        sock.close()

    return devices


def scan_mdns(timeout: float = 5.0,
              on_device: Callable[[Device], None] = None) -> List[Device]:
    """Discover AirPlay, Chromecast, and other mDNS devices."""
    devices: List[Device] = []
    try:
        from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
    except ImportError:
        logger.warning("zeroconf not installed — mDNS scan skipped")
        return []

    services_to_watch = [
        ("_googlecast._tcp.local.", Protocol.CHROMECAST, DeviceType.TV),
        ("_airplay._tcp.local.", Protocol.AIRPLAY, DeviceType.TV),
        ("_mediarss._tcp.local.", Protocol.DLNA, DeviceType.TV),
        ("_http._tcp.local.", Protocol.WIFI, DeviceType.UNKNOWN),
    ]

    seen = set()
    zc = Zeroconf()

    class Listener:
        def __init__(self, protocol, device_type):
            self.protocol = protocol
            self.device_type = device_type

        def add_service(self, zc_ref, type_, name):
            try:
                info = zc_ref.get_service_info(type_, name, timeout=2000)
                if not info:
                    return
                addresses = info.parsed_addresses()
                if not addresses:
                    return
                ip = addresses[0]
                if ip in seen:
                    return
                seen.add(ip)

                friendly = (info.properties.get(b"fn") or
                            info.properties.get(b"md") or
                            b"").decode("utf-8", errors="ignore")
                device_name = friendly or name.split(".")[0]
                model = (info.properties.get(b"md") or b"").decode("utf-8", errors="ignore")

                device = Device(
                    id=f"mdns_{ip}",
                    name=device_name,
                    device_type=self.device_type,
                    protocol=self.protocol,
                    address=ip,
                    port=info.port,
                    model=model or None,
                    extra={"mdns_name": name},
                )
                devices.append(device)
                if on_device:
                    on_device(device)
            except Exception as e:
                logger.debug(f"mDNS service info error: {e}")

        def remove_service(self, *_):
            pass

        def update_service(self, *_):
            pass

    browsers = []
    for service_type, protocol, device_type in services_to_watch:
        listener = Listener(protocol, device_type)
        browser = ServiceBrowser(zc, service_type, listener)
        browsers.append(browser)

    import time
    time.sleep(timeout)
    zc.close()
    return devices


def scan_network(timeout: float = 8.0,
                 on_device: Callable[[Device], None] = None) -> List[Device]:
    """Run SSDP and mDNS in parallel, merge results."""
    results: List[Device] = []
    seen_ids: set = set()
    lock = threading.Lock()

    def add(device: Device):
        with lock:
            if device.id not in seen_ids:
                seen_ids.add(device.id)
                results.append(device)
                if on_device:
                    on_device(device)

    threads = [
        threading.Thread(target=lambda: [add(d) for d in scan_ssdp(timeout, None)], daemon=True),
        threading.Thread(target=lambda: [add(d) for d in scan_mdns(timeout, None)], daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout + 2)

    return results
