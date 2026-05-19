"""Main GUI window using customtkinter."""
import asyncio
import logging
import threading
from typing import List, Optional

import customtkinter as ctk

from config_manager import ConfigManager
from discovery.models import Device, DeviceType, Protocol
from discovery.network_scanner import scan_network
from discovery.bluetooth_scanner import scan_bluetooth
from connectors.miracast import connect_miracast_device, set_display_mode, open_connect_ui
from connectors.chromecast import ChromecastConnector
from connectors.bluetooth_conn import BluetoothConnector
from connectors.mobile import AirPlayConnector, AndroidConnector

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PROTOCOL_COLOR = {
    Protocol.WIFI: "#1E90FF",
    Protocol.CHROMECAST: "#EA4335",
    Protocol.DLNA: "#4CAF50",
    Protocol.BLUETOOTH: "#9C27B0",
    Protocol.MIRACAST: "#2196F3",
    Protocol.AIRPLAY: "#FF9800",
    Protocol.INFRARED: "#607D8B",
}

TYPE_ICON = {
    DeviceType.TV: "📺",
    DeviceType.BOX: "📦",
    DeviceType.CONSOLE: "🎮",
    DeviceType.SPEAKER: "🔊",
    DeviceType.PROJECTOR: "📽",
    DeviceType.UNKNOWN: "📡",
}


class DeviceCard(ctk.CTkFrame):
    def __init__(self, master, device: Device, config: ConfigManager,
                 on_connect=None, on_favorite=None, **kwargs):
        super().__init__(master, corner_radius=12, **kwargs)
        self.device = device
        self.config = config
        self.on_connect = on_connect
        self.on_favorite = on_favorite

        self._build()

    def _build(self):
        icon = TYPE_ICON.get(self.device.device_type, "📡")
        color = PROTOCOL_COLOR.get(self.device.protocol, "#607D8B")
        is_fav = self.config.is_favorite(self.device.id)

        # Left: icon
        ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 28)).grid(
            row=0, column=0, rowspan=2, padx=(16, 8), pady=12)

        # Center: name + protocol badge
        ctk.CTkLabel(self, text=self.device.display_name,
                     font=("Segoe UI", 14, "bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", padx=4)

        badge = ctk.CTkLabel(self,
                              text=f"  {self.device.protocol_label}  ",
                              font=("Segoe UI", 10),
                              fg_color=color, corner_radius=8,
                              text_color="white")
        badge.grid(row=1, column=1, sticky="w", padx=4)

        # Model / address info
        info = self.device.address
        if self.device.model:
            info = f"{self.device.model} · {info}"
        ctk.CTkLabel(self, text=info, font=("Segoe UI", 10),
                     text_color="gray", anchor="w").grid(
            row=2, column=1, sticky="w", padx=4, pady=(0, 8))

        # Right: buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=3, padx=12, pady=8, sticky="e")

        ctk.CTkButton(btn_frame, text="Connecter", width=110, height=32,
                      command=self._connect).pack(pady=(0, 6))

        fav_text = "★ Favori" if not is_fav else "✕ Retirer"
        ctk.CTkButton(btn_frame, text=fav_text, width=110, height=28,
                      fg_color="transparent", border_width=1,
                      command=self._toggle_favorite).pack()

        self.columnconfigure(1, weight=1)

    def _connect(self):
        if self.on_connect:
            self.on_connect(self.device)

    def _toggle_favorite(self):
        if self.on_favorite:
            self.on_favorite(self.device)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Universal TV Bridge")
        self.geometry("900x700")
        self.resizable(True, True)

        self.config_mgr = ConfigManager()
        self._devices: List[Device] = []
        self._scanning = False
        self._bt_connector = BluetoothConnector()
        self._cast_connector = ChromecastConnector()
        self._airplay = AirPlayConnector()
        self._android = AndroidConnector()

        self._build_ui()
        self._load_favorites()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, height=70, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="📺  Universal TV Bridge",
                     font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, padx=20, pady=18, sticky="w")

        # Scan button
        self.scan_btn = ctk.CTkButton(
            header, text="🔍  Scanner", width=130, height=38,
            command=self._start_scan)
        self.scan_btn.grid(row=0, column=2, padx=8)

        # Miracast button
        ctk.CTkButton(
            header, text="📡  Miracast", width=130, height=38,
            fg_color="#2196F3", command=open_connect_ui
        ).grid(row=0, column=3, padx=8)

        # Display mode
        mode_menu = ctk.CTkOptionMenu(
            header,
            values=["Étendre", "Dupliquer", "PC uniquement", "TV uniquement"],
            command=self._set_display_mode,
            width=160, height=38
        )
        mode_menu.grid(row=0, column=4, padx=(8, 20))

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))

        self.tab_devices = self.tabview.add("Appareils")
        self.tab_favorites = self.tabview.add("Favoris")
        self.tab_mobile = self.tabview.add("Mobile (iOS/Android)")
        self.tab_ir = self.tabview.add("Infrarouge")

        self._build_devices_tab()
        self._build_favorites_tab()
        self._build_mobile_tab()
        self._build_ir_tab()

        # Status bar
        self.status_var = ctk.StringVar(value="Prêt · Cliquez sur Scanner pour détecter les appareils")
        ctk.CTkLabel(self, textvariable=self.status_var,
                     font=("Segoe UI", 11), text_color="gray",
                     anchor="w").grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

    def _build_devices_tab(self):
        self.tab_devices.grid_columnconfigure(0, weight=1)
        self.tab_devices.grid_rowconfigure(1, weight=1)

        # Filter bar
        filter_frame = ctk.CTkFrame(self.tab_devices, fg_color="transparent")
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(filter_frame, text="Filtrer :").pack(side="left", padx=(0, 8))
        self.filter_var = ctk.StringVar(value="Tous")
        for label in ["Tous", "TV", "Box", "Console", "Bluetooth", "WiFi"]:
            ctk.CTkButton(filter_frame, text=label, width=70, height=28,
                          fg_color="transparent", border_width=1,
                          command=lambda l=label: self._apply_filter(l)).pack(
                side="left", padx=3)

        # Scrollable device list
        self.device_scroll = ctk.CTkScrollableFrame(self.tab_devices)
        self.device_scroll.grid(row=1, column=0, sticky="nsew")
        self.device_scroll.grid_columnconfigure(0, weight=1)

        # Spinner label
        self.spinner_label = ctk.CTkLabel(
            self.device_scroll, text="Aucun appareil détecté.\nCliquez sur Scanner.",
            font=("Segoe UI", 13), text_color="gray")
        self.spinner_label.grid(row=0, column=0, pady=60)

    def _build_favorites_tab(self):
        self.tab_favorites.grid_columnconfigure(0, weight=1)
        self.tab_favorites.grid_rowconfigure(0, weight=1)
        self.fav_scroll = ctk.CTkScrollableFrame(self.tab_favorites)
        self.fav_scroll.grid(row=0, column=0, sticky="nsew")
        self.fav_scroll.grid_columnconfigure(0, weight=1)

    def _build_mobile_tab(self):
        self.tab_mobile.grid_columnconfigure(0, weight=1)

        # iOS section
        ios_frame = ctk.CTkFrame(self.tab_mobile)
        ios_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ios_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ios_frame, text="iPhone / iPad (AirPlay)",
                     font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(ios_frame,
                     text="Pour recevoir l'écran iPhone sur ce PC, un récepteur AirPlay est nécessaire.",
                     text_color="gray", wraplength=700, justify="left").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        btn_row = ctk.CTkFrame(ios_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Lancer AirServer",
                      command=self._launch_airplay_receiver).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Télécharger AirServer",
                      fg_color="transparent", border_width=1,
                      command=self._airplay.open_download_page).pack(side="left")

        # Android section
        and_frame = ctk.CTkFrame(self.tab_mobile)
        and_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        and_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(and_frame, text="Android (ADB / scrcpy / Miracast)",
                     font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        btn_row2 = ctk.CTkFrame(and_frame, fg_color="transparent")
        btn_row2.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))
        ctk.CTkButton(btn_row2, text="Miroir écran (scrcpy)",
                      command=self._mirror_android).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row2, text="Télécharger scrcpy",
                      fg_color="transparent", border_width=1,
                      command=self._android.open_scrcpy_download).pack(side="left")

        # ADB WiFi row
        adb_row = ctk.CTkFrame(and_frame, fg_color="transparent")
        adb_row.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkLabel(adb_row, text="IP Android :").pack(side="left", padx=(0, 6))
        self.adb_ip_entry = ctk.CTkEntry(adb_row, width=160, placeholder_text="192.168.1.XX")
        self.adb_ip_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(adb_row, text="Connecter ADB WiFi",
                      command=self._connect_adb_wifi).pack(side="left")

        # ADB devices list
        self.adb_devices_label = ctk.CTkLabel(and_frame, text="",
                                               text_color="gray", anchor="w")
        self.adb_devices_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(and_frame, text="Actualiser appareils ADB",
                      width=200,
                      command=self._refresh_adb_devices).grid(
            row=4, column=0, sticky="w", padx=16, pady=(0, 12))

    def _build_ir_tab(self):
        self.tab_ir.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.tab_ir,
                     text="Télécommande Infrarouge",
                     font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(self.tab_ir,
                     text="Nécessite un émetteur IR USB (USB-UIRT, WinLIRC, etc.)",
                     text_color="gray").grid(row=1, column=0, sticky="w", padx=16)

        ctrl_frame = ctk.CTkFrame(self.tab_ir)
        ctrl_frame.grid(row=2, column=0, padx=16, pady=16, sticky="w")

        ctk.CTkLabel(ctrl_frame, text="Marque TV :").grid(row=0, column=0, padx=12, pady=8)
        self.ir_brand = ctk.CTkOptionMenu(ctrl_frame,
                                           values=["samsung", "lg", "sony", "philips"],
                                           width=140)
        self.ir_brand.grid(row=0, column=1, padx=8, pady=8)

        commands = [
            ("⏻ Power", "power"), ("🔊+", "volume_up"), ("🔉-", "volume_down"),
            ("🔇 Mute", "mute"), ("HDMI 1", "hdmi1"), ("HDMI 2", "hdmi2"),
        ]
        for i, (label, cmd) in enumerate(commands):
            ctk.CTkButton(ctrl_frame, text=label, width=110,
                          command=lambda c=cmd: self._ir_send(c)).grid(
                row=1 + i // 3, column=i % 3, padx=8, pady=6)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _start_scan(self):
        if self._scanning:
            return
        self._scanning = True
        self.scan_btn.configure(state="disabled", text="Scan en cours...")
        self._set_status("Scan en cours… (WiFi + Bluetooth)")
        self._clear_device_list()
        self.spinner_label.configure(text="Recherche en cours…")

        def run():
            found = []
            lock = threading.Lock()

            def on_device(device: Device):
                with lock:
                    found.append(device)
                self.after(0, lambda d=device: self._add_device_card(d))

            # Network scan
            t1 = threading.Thread(
                target=lambda: scan_network(timeout=6, on_device=on_device), daemon=True)
            # Bluetooth scan
            t2 = threading.Thread(
                target=lambda: asyncio.run(scan_bluetooth(timeout=8, on_device=on_device)),
                daemon=True)

            t1.start(); t2.start()
            t1.join(); t2.join()

            self.after(0, self._scan_finished, len(found))

        threading.Thread(target=run, daemon=True).start()

    def _scan_finished(self, count: int):
        self._scanning = False
        self.scan_btn.configure(state="normal", text="🔍  Scanner")
        msg = f"{count} appareil(s) détecté(s)" if count else "Aucun appareil détecté"
        self._set_status(msg)
        if count == 0:
            self.spinner_label.configure(text="Aucun appareil détecté.\nVérifiez que les appareils sont allumés.")
        else:
            self.spinner_label.grid_remove()

    def _clear_device_list(self):
        for widget in self.device_scroll.winfo_children():
            widget.destroy()
        self.spinner_label = ctk.CTkLabel(
            self.device_scroll, text="Recherche en cours…",
            font=("Segoe UI", 13), text_color="gray")
        self.spinner_label.grid(row=0, column=0, pady=60)
        self._devices.clear()

    def _add_device_card(self, device: Device):
        if device in self._devices:
            return
        self._devices.append(device)
        if self.spinner_label.winfo_exists():
            self.spinner_label.grid_remove()
        row = len(self._devices) - 1
        card = DeviceCard(self.device_scroll, device, self.config_mgr,
                          on_connect=self._connect_device,
                          on_favorite=self._toggle_favorite)
        card.grid(row=row, column=0, sticky="ew", pady=4, padx=4)

    def _apply_filter(self, label: str):
        # Re-render filtered list
        self._clear_device_list()
        self.spinner_label.grid_remove()
        filter_map = {
            "TV": DeviceType.TV, "Box": DeviceType.BOX,
            "Console": DeviceType.CONSOLE,
        }
        proto_map = {
            "Bluetooth": Protocol.BLUETOOTH, "WiFi": Protocol.WIFI,
        }
        devices_copy = list(self._devices)
        self._devices.clear()

        for device in devices_copy:
            if label == "Tous":
                pass
            elif label in filter_map and device.device_type != filter_map[label]:
                continue
            elif label in proto_map and device.protocol != proto_map[label]:
                continue
            self._add_device_card(device)

        if not self._devices:
            self.spinner_label.configure(text=f"Aucun appareil « {label} » détecté.")
            self.spinner_label.grid(row=0, column=0, pady=60)

    def _connect_device(self, device: Device):
        self._set_status(f"Connexion à {device.display_name}…")
        self.config_mgr.set_last_connected(device)

        def do_connect():
            ok = False
            if device.protocol == Protocol.MIRACAST:
                ok = connect_miracast_device(device.name)
            elif device.protocol == Protocol.CHROMECAST:
                ok = self._cast_connector.connect(device.address, device.port or 8009)
            elif device.protocol == Protocol.BLUETOOTH:
                ok = self._bt_connector.connect(device.address)
            else:
                ok = open_connect_ui()
            msg = f"Connecté à {device.display_name}" if ok else f"Échec connexion à {device.display_name}"
            self.after(0, lambda: self._set_status(msg))

        threading.Thread(target=do_connect, daemon=True).start()

    def _toggle_favorite(self, device: Device):
        if self.config_mgr.is_favorite(device.id):
            self.config_mgr.remove_favorite(device.id)
        else:
            self.config_mgr.add_favorite(device)
        self._load_favorites()

    def _load_favorites(self):
        for w in self.fav_scroll.winfo_children():
            w.destroy()
        favs = self.config_mgr.get_favorites()
        if not favs:
            ctk.CTkLabel(self.fav_scroll,
                         text="Aucun favori. Ajoutez des appareils depuis l'onglet Appareils.",
                         text_color="gray").pack(pady=40)
            return
        for i, dev in enumerate(favs):
            card = DeviceCard(self.fav_scroll, dev, self.config_mgr,
                              on_connect=self._connect_device,
                              on_favorite=self._toggle_favorite)
            card.grid(row=i, column=0, sticky="ew", pady=4, padx=4)

    def _set_display_mode(self, label: str):
        modes = {
            "Étendre": "extend", "Dupliquer": "clone",
            "PC uniquement": "internal", "TV uniquement": "external",
        }
        mode = modes.get(label, "extend")
        set_display_mode(mode)
        self._set_status(f"Mode affichage : {label}")

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    # ── Mobile ──────────────────────────────────────────────────────────────────

    def _launch_airplay_receiver(self):
        ok = self._airplay.launch_receiver()
        if not ok:
            self._set_status("Aucun récepteur AirPlay trouvé — téléchargez AirServer")
        else:
            self._set_status("Récepteur AirPlay lancé")

    def _mirror_android(self):
        ok = self._android.mirror_screen()
        if not ok:
            self._set_status("scrcpy non trouvé — téléchargez-le d'abord")
        else:
            self._set_status("Miroir Android lancé (scrcpy)")

    def _connect_adb_wifi(self):
        ip = self.adb_ip_entry.get().strip()
        if not ip:
            self._set_status("Entrez l'adresse IP de l'appareil Android")
            return

        def do():
            ok = self._android.connect_adb_wifi(ip)
            msg = f"ADB WiFi connecté : {ip}" if ok else f"Échec ADB WiFi : {ip} (vérifiez le débogage USB)"
            self.after(0, lambda: self._set_status(msg))

        threading.Thread(target=do, daemon=True).start()

    def _refresh_adb_devices(self):
        devices = self._android.list_adb_devices()
        if devices:
            text = "Appareils ADB : " + ", ".join(f"{d['model']} ({d['serial']})" for d in devices)
        else:
            text = "Aucun appareil ADB connecté"
        self.adb_devices_label.configure(text=text)

    # ── Infrared ────────────────────────────────────────────────────────────────

    def _ir_send(self, command: str):
        from discovery.infrared import get_ir_controller
        brand = self.ir_brand.get()
        ctrl = get_ir_controller()
        if not ctrl.available:
            self._set_status("Aucun émetteur IR détecté (USB-UIRT/WinLIRC requis)")
            return
        ok = ctrl.send_code(brand, command)
        self._set_status(f"IR {brand}/{command} {'envoyé' if ok else 'échec'}")
