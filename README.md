# Universal TV Bridge

Détection et connexion automatique PC ↔ TV/Box/Console/Mobile via tous les protocoles.

## Protocoles supportés

| Protocole | Appareils |
|-----------|-----------|
| **WiFi / SSDP / UPnP** | Smart TV Samsung, LG, Sony, Hisense… |
| **mDNS / Bonjour** | Chromecast, Apple TV, TVs réseau |
| **Bluetooth LE** | TV, enceintes, consoles BT |
| **Miracast** | TV compatible Windows Wireless Display |
| **DLNA** | Lecteurs média, TV DLNA |
| **AirPlay** | iPhone, iPad, Apple TV |
| **ADB / scrcpy** | Android (USB + WiFi) |
| **Infrarouge** | TV Samsung/LG/Sony/Philips (émetteur USB requis) |

## Installation

```bash
pip install -r requirements.txt
python main.py
```

Ou double-cliquer `install.bat` puis lancer `python main.py`.

## Fonctionnalités

- **Scan automatique** : détecte tous les appareils sur le réseau + Bluetooth
- **Connexion en 1 clic** : Miracast, Chromecast, DLNA, BT
- **Mode affichage** : Étendre / Dupliquer / PC uniquement / TV uniquement
- **Mobile iOS** : réception AirPlay via AirServer / 5KPlayer
- **Mobile Android** : miroir écran via scrcpy, connexion ADB WiFi
- **Télécommande IR** : contrôle infrarouge (nécessite émetteur USB-UIRT/WinLIRC)
- **Favoris** : sauvegarde des appareils préférés

## Dépendances matérielles optionnelles

| Fonctionnalité | Matériel requis |
|----------------|-----------------|
| Infrarouge | USB-UIRT ou émetteur WinLIRC |
| AirPlay receiver | AirServer (payant) ou 5KPlayer (gratuit) |
| Android miroir | scrcpy (gratuit, open-source) |
| Android ADB WiFi | Mode développeur activé sur l'Android |

## Architecture

```
universal-tv-bridge/
├── main.py                   # Point d'entrée
├── config_manager.py         # Persistance des favoris
├── discovery/
│   ├── models.py             # Device, DeviceType, Protocol
│   ├── bluetooth_scanner.py  # Scan BLE (bleak)
│   ├── network_scanner.py    # SSDP + mDNS
│   └── infrared.py           # Contrôle IR
├── connectors/
│   ├── miracast.py           # Windows Wireless Display
│   ├── chromecast.py         # Google Cast
│   ├── bluetooth_conn.py     # Connexion BT
│   ├── dlna.py               # DLNA/UPnP renderer
│   └── mobile.py             # iOS AirPlay + Android ADB
└── ui/
    └── main_window.py        # Interface customtkinter
```
