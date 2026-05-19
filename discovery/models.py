from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceType(Enum):
    TV = "tv"
    BOX = "box"
    CONSOLE = "console"
    SPEAKER = "speaker"
    PROJECTOR = "projector"
    UNKNOWN = "unknown"


class Protocol(Enum):
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    MIRACAST = "miracast"
    CHROMECAST = "chromecast"
    DLNA = "dlna"
    AIRPLAY = "airplay"
    INFRARED = "infrared"


@dataclass
class Device:
    id: str
    name: str
    device_type: DeviceType
    protocol: Protocol
    address: str
    port: Optional[int] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    rssi: Optional[int] = None
    extra: dict = field(default_factory=dict)
    connected: bool = False

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Device) and self.id == other.id

    @property
    def display_name(self) -> str:
        if self.manufacturer and self.manufacturer.lower() not in self.name.lower():
            return f"{self.manufacturer} {self.name}"
        return self.name

    @property
    def protocol_label(self) -> str:
        labels = {
            Protocol.WIFI: "WiFi",
            Protocol.BLUETOOTH: "Bluetooth",
            Protocol.MIRACAST: "Miracast",
            Protocol.CHROMECAST: "Chromecast",
            Protocol.DLNA: "DLNA/UPnP",
            Protocol.AIRPLAY: "AirPlay",
            Protocol.INFRARED: "Infrarouge",
        }
        return labels.get(self.protocol, self.protocol.value)
