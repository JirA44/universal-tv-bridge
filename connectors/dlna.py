"""DLNA/UPnP media renderer connector."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DLNAConnector:
    def __init__(self, location_url: str):
        self.location_url = location_url
        self._renderer = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import upnpclient
            return True
        except ImportError:
            logger.warning("upnpclient not installed")
            return False

    def connect(self) -> bool:
        if not self._available:
            return False
        try:
            import upnpclient
            self._renderer = upnpclient.Device(self.location_url)
            logger.info(f"DLNA connected: {self._renderer.friendly_name}")
            return True
        except Exception as e:
            logger.error(f"DLNA connect error: {e}")
            return False

    def play(self, url: str, metadata: str = "") -> bool:
        if not self._renderer:
            return False
        try:
            avt = self._renderer["AVTransport"]
            avt.SetAVTransportURI(
                InstanceID=0,
                CurrentURI=url,
                CurrentURIMetaData=metadata,
            )
            avt.Play(InstanceID=0, Speed="1")
            return True
        except Exception as e:
            logger.error(f"DLNA play error: {e}")
            return False

    def stop(self) -> bool:
        if not self._renderer:
            return False
        try:
            avt = self._renderer["AVTransport"]
            avt.Stop(InstanceID=0)
            return True
        except Exception as e:
            logger.error(f"DLNA stop error: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """volume: 0-100"""
        if not self._renderer:
            return False
        try:
            rc = self._renderer["RenderingControl"]
            rc.SetVolume(InstanceID=0, Channel="Master", DesiredVolume=max(0, min(100, volume)))
            return True
        except Exception as e:
            logger.error(f"DLNA volume error: {e}")
            return False

    @property
    def name(self) -> str:
        if self._renderer:
            return getattr(self._renderer, "friendly_name", "DLNA Device")
        return "DLNA Device"
