"""Bluetooth device connector (BLE + classic via Windows shell)."""
import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)


async def connect_ble(address: str) -> bool:
    """Connect to a BLE device by address."""
    try:
        from bleak import BleakClient
        client = BleakClient(address)
        await client.connect()
        if client.is_connected:
            logger.info(f"BLE connected: {address}")
            return True
        return False
    except ImportError:
        logger.warning("bleak not installed")
        return False
    except Exception as e:
        logger.error(f"BLE connect error: {e}")
        return False


def pair_bluetooth_windows(address: str) -> bool:
    """
    Pair a Bluetooth device on Windows via DevicePairingKinds.
    Opens Bluetooth settings for the user to confirm pairing.
    """
    try:
        subprocess.Popen(
            ["ms-settings:bluetooth"],
            shell=True,
        )
        return True
    except Exception as e:
        logger.error(f"Cannot open Bluetooth settings: {e}")
        return False


def open_bluetooth_settings():
    """Open Windows Bluetooth & devices settings."""
    subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)


class BluetoothConnector:
    def __init__(self):
        self._loop = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop

    def connect(self, address: str) -> bool:
        loop = self._get_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, connect_ble(address))
                return future.result(timeout=15)
        return loop.run_until_complete(connect_ble(address))

    def open_settings(self):
        open_bluetooth_settings()
