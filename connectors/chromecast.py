"""Google Chromecast / Google Cast connector."""
import logging
import threading
from typing import List, Optional

logger = logging.getLogger(__name__)


class ChromecastConnector:
    def __init__(self):
        self._cast = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import pychromecast
            return True
        except ImportError:
            logger.warning("pychromecast not installed")
            return False

    @property
    def available(self) -> bool:
        return self._available

    def discover(self, timeout: float = 5.0) -> List[dict]:
        if not self._available:
            return []
        try:
            import pychromecast
            chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
            pychromecast.discovery.stop_discovery(browser)
            return [
                {"name": cc.name, "host": cc.host, "port": cc.port,
                 "model": cc.model_name, "uuid": str(cc.uuid)}
                for cc in chromecasts
            ]
        except Exception as e:
            logger.error(f"Chromecast discovery error: {e}")
            return []

    def connect(self, host: str, port: int = 8009) -> bool:
        if not self._available:
            return False
        try:
            import pychromecast
            cast = pychromecast.get_chromecast_from_host((host, port, None, None, None))
            cast.wait(timeout=10)
            self._cast = cast
            logger.info(f"Connected to Chromecast at {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Chromecast connect error: {e}")
            return False

    def cast_url(self, url: str, content_type: str = "video/mp4") -> bool:
        if not self._cast:
            return False
        try:
            mc = self._cast.media_controller
            mc.play_media(url, content_type)
            mc.block_until_active(timeout=30)
            return True
        except Exception as e:
            logger.error(f"Chromecast cast error: {e}")
            return False

    def stop(self) -> bool:
        if not self._cast:
            return False
        try:
            self._cast.quit_app()
            return True
        except Exception as e:
            logger.error(f"Chromecast stop error: {e}")
            return False

    def disconnect(self):
        if self._cast:
            try:
                self._cast.disconnect()
            except Exception:
                pass
            self._cast = None
