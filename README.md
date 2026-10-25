# Universal TV Bridge

Universal TV Bridge est une application Windows qui cherche des téléviseurs, boîtiers et appareils compatibles sur le réseau local ou en Bluetooth, puis propose les connecteurs pris en charge pour les utiliser depuis le PC.

## À quoi sert cet outil ?

Il rassemble dans une seule interface la découverte d’appareils et plusieurs moyens de connexion ou de contrôle : Cast, DLNA/UPnP, Bluetooth, Miracast, AirPlay, ADB et infrarouge.

## Pourquoi l’utiliser ?

Les appareils de salon n’utilisent pas tous le même protocole. Au lieu de chercher manuellement comment chaque appareil se connecte, l’application aide à repérer les appareils disponibles et à choisir un connecteur compatible.

La compatibilité dépend du modèle, du réseau, des composants installés et parfois d’un matériel externe. La présence d’un protocole dans la liste ne garantit pas que chaque appareil ou fonction soit pris en charge.

## Exemples d’utilisation

- **Projeter ou étendre l’affichage du PC** : rechercher une TV compatible Miracast et utiliser le mode d’affichage Windows approprié.
- **Lire un média sur une TV du réseau** : rechercher un récepteur DLNA ou Chromecast puis utiliser son connecteur si le modèle le permet.
- **Afficher un appareil Android** : connecter l’appareil par USB ou ADB Wi-Fi et utiliser scrcpy, qui doit être installé séparément.
- **Contrôler une TV en infrarouge** : connecter un émetteur USB compatible ; le PC seul ne dispose généralement pas de cette fonction.
- **Retrouver un appareil utilisé souvent** : enregistrer l’appareil comme favori si la connexion a été établie.

## Installation et démarrage

Prérequis : Python et les dépendances listées dans `requirements.txt`. Certaines fonctions nécessitent des outils ou matériels optionnels.

```powershell
python -m pip install -r requirements.txt
python main.py
```

On peut aussi lancer `install.bat`, puis `python main.py`.

## English

### What is Universal TV Bridge for?

Universal TV Bridge is a Windows application that discovers compatible TVs, streaming boxes, and other devices on a local network or over Bluetooth, then offers available connection methods.

### Why use it?

Home devices use different protocols. The app provides one place to discover nearby devices and select a compatible connector instead of searching for each connection method separately.

### Examples

- Find a Miracast-compatible TV to extend or mirror the PC display.
- Discover a Chromecast or DLNA receiver on the local network.
- Mirror an Android device using ADB and scrcpy, installed separately.
- Use infrared control only when a compatible USB transmitter is connected.

Support depends on the device, network, Windows capabilities, and optional hardware or software. A listed protocol does not guarantee that every device supports every feature.


## Protocoles et dépendances optionnelles

| Protocole ou fonction | Dépendance ou limite |
| --- | --- |
| SSDP/UPnP, mDNS | Appareils visibles sur le même réseau local |
| Bluetooth LE | Adaptateur Bluetooth et appareil compatible |
| Miracast | Prise en charge par Windows, l’adaptateur et la TV |
| DLNA / Chromecast | Récepteur compatible accessible sur le réseau |
| AirPlay | Récepteur AirPlay tel qu’AirServer ou 5KPlayer |
| Android via ADB / scrcpy | Mode développeur et outils ADB/scrcpy |
| Infrarouge | Émetteur USB-UIRT ou matériel compatible WinLIRC |

## Architecture

```text
universal-tv-bridge/
├── main.py
├── config_manager.py
├── discovery/       découverte réseau, Bluetooth et infrarouge
├── connectors/      connecteurs par protocole
└── ui/              interface CustomTkinter
```
