# BlueMan Wind
Consider this my attempt against microslop's awful bluetooth implementation 
**BlueMan Wind** is a Windows Bluetooth management utility designed to provide deeper control over Bluetooth devices than the default Windows interface.

It supports scanning, pairing, unpairing, battery monitoring, and BLE/GATT inspection through a command-line interface built on top of Windows WinRT APIs and BLE tooling.

The project is part of a larger effort to build a **fully featured Bluetooth manager for Windows**, eventually including:

* Automatic reconnect service
* Multi-device audio sharing
* Battery monitoring widgets
* Quick Settings integration
* GUI companion application

---

## Features

* Scan **Classic Bluetooth and BLE devices simultaneously**
* Display **RSSI signal strength**
* Show **battery levels** when available
* Pair devices
* Unpair devices
* Retrieve battery level via:

  * Windows device properties
  * WinRT queries
  * PowerShell fallback
* Inspect **GATT services and characteristics**
* Lightweight CLI interface

---

## Project Structure

```
.
├── main.py                 # CLI interface
├── win_bluetooth.py        # Windows Bluetooth manager backend
├── bleak_detection.py      # BLE device scanning example
├── bleak_auto_reconnect.py # BLE auto connect test
├── bleak_gatt_test.py      # GATT service inspection tool
├── README.md
└── .gitignore
```

---

## Requirements

* Windows 10 / Windows 11
* Python 3.9+

### Python Libraries

```
bleak
winsdk
```

Install dependencies:

```bash
pip install bleak winsdk
```

---

## Usage

Run the CLI:

```bash
python main.py
```

Available commands inside the CLI:

```
s  → Scan for Bluetooth devices
p  → Pair device
u  → Unpair device
b  → Check device battery level
q  → Quit
```

Devices are displayed with:

```
IDX | TYPE | RSSI | BATT | NAME
```

Example:

```
0 | Classic | -45 | 90% | Sony WH-1000XM4
1 | BLE     | -60 | --  | Mi Band
```

---

## Battery Retrieval System

Battery levels are retrieved using a **hybrid system**:

1. Windows device properties (fastest)
2. WinRT device queries
3. PowerShell fallback

This allows the tool to retrieve battery levels for most Bluetooth headphones, earbuds, and peripherals.

---

## Future Roadmap

Planned features:

* Automatic Bluetooth reconnect service
* Desktop battery widgets
* Windows Quick Settings toggle
* Multi-device Bluetooth audio sharing
* Full WinUI GUI application
* Device profiles and management

---

## License

MIT License

---

## Author

Srijan Das
