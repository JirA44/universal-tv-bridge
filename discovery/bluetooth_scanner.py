import asyncio
import logging
from typing import Callable, List

from .models import Device, DeviceType, Protocol

logger = logging.getLogger(__name__)

TV_KEYWORDS = {"tv", "samsung", "lg", "sony", "philips", "tcl", "hisense", "panasonic",
               "vizio", "sharp", "toshiba", "bravia", "qled", "oled"}
BOX_KEYWORDS = {"freebox", "livebox", "bbox", "sfr", "neufbox", "orange", "bouygues"}
CONSOLE_KEYWORDS = {"playstation", "ps4", "ps5", "xbox", "nintendo", "switch"}
SPEAKER_KEYWORDS = {"speaker", "soundbar", "bose", "sonos", "jbl", "harman", "denon"}


def _classify_bt_device(name: str) -> DeviceType:
    lower = name.lower()
    if any(k in lower for k in TV_KEYWORDS):
        return DeviceType.TV
    if any(k in lower for k in BOX_KEYWORDS):
        return DeviceType.BOX
    if any(k in lower for k in CONSOLE_KEYWORDS):
        return DeviceType.CONSOLE
    if any(k in lower for k in SPEAKER_KEYWORDS):
        return DeviceType.SPEAKER
    return DeviceType.UNKNOWN


async def scan_bluetooth(timeout: float = 10.0,
                         on_device: Callable[[Device], None] = None) -> List[Device]:
    try:
        from bleak import BleakScanner
    except ImportError:
        logger.warning("bleak not installed — Bluetooth scan skipped")
        return []

    devices: List[Device] = []
    seen = set()

    def detection_callback(bt_device, advertisement_data):
        if bt_device.address in seen:
            return
        seen.add(bt_device.address)

        name = bt_device.name or advertisement_data.local_name or "Unknown BT"
        device = Device(
            id=f"bt_{bt_device.address}",
            name=name,
            device_type=_classify_bt_device(name),
            protocol=Protocol.BLUETOOTH,
            address=bt_device.address,
            rssi=advertisement_data.rssi,
        )
        devices.append(device)
        if on_device:
            on_device(device)

    try:
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
    except Exception as e:
        logger.error(f"Bluetooth scan error: {e}")

    return devices
