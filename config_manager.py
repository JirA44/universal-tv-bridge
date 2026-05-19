"""Persistent device configuration and favorites."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from discovery.models import Device, DeviceType, Protocol

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".universal-tv-bridge"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _device_to_dict(device: Device) -> dict:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": device.device_type.value,
        "protocol": device.protocol.value,
        "address": device.address,
        "port": device.port,
        "model": device.model,
        "manufacturer": device.manufacturer,
        "extra": device.extra,
    }


def _dict_to_device(data: dict) -> Device:
    return Device(
        id=data["id"],
        name=data["name"],
        device_type=DeviceType(data.get("device_type", "unknown")),
        protocol=Protocol(data.get("protocol", "wifi")),
        address=data["address"],
        port=data.get("port"),
        model=data.get("model"),
        manufacturer=data.get("manufacturer"),
        extra=data.get("extra", {}),
    )


class ConfigManager:
    def __init__(self):
        _ensure_config_dir()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Config load error: {e}")
        return {"favorites": [], "last_connected": None, "settings": {}}

    def _save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Config save error: {e}")

    def get_favorites(self) -> List[Device]:
        return [_dict_to_device(d) for d in self._data.get("favorites", [])]

    def add_favorite(self, device: Device):
        favs = self._data.setdefault("favorites", [])
        if not any(d["id"] == device.id for d in favs):
            favs.append(_device_to_dict(device))
            self._save()

    def remove_favorite(self, device_id: str):
        favs = self._data.get("favorites", [])
        self._data["favorites"] = [d for d in favs if d["id"] != device_id]
        self._save()

    def is_favorite(self, device_id: str) -> bool:
        return any(d["id"] == device_id for d in self._data.get("favorites", []))

    def set_last_connected(self, device: Device):
        self._data["last_connected"] = _device_to_dict(device)
        self._save()

    def get_last_connected(self) -> Optional[Device]:
        data = self._data.get("last_connected")
        return _dict_to_device(data) if data else None

    def get_setting(self, key: str, default=None):
        return self._data.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value):
        self._data.setdefault("settings", {})[key] = value
        self._save()
