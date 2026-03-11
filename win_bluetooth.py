import asyncio
import subprocess
from typing import List, Dict, Optional

# --- WinSDK Imports ---
from winsdk.windows.devices.enumeration import (
    DeviceInformation,
    DeviceWatcher,
    DeviceInformationKind,
    DevicePairingResultStatus,
    DeviceUnpairingResultStatus,
    DevicePairingKinds,
    DevicePairingProtectionLevel,
)

from winsdk.windows.devices.bluetooth.advertisement import (
    BluetoothLEAdvertisementWatcher,
    BluetoothLEScanningMode,
    BluetoothLEAdvertisementReceivedEventArgs,
)

from winsdk.windows.devices.bluetooth import BluetoothLEDevice
from winsdk.windows.devices.bluetooth.genericattributeprofile import (
    GattCharacteristic,
    GattCommunicationStatus,
)

from uuid import UUID


# --- CONSTANTS ---
CLASSIC_PROTOCOL_ID = "{e0cbf06c-cd8b-4647-bb8a-263b43f0f974}"
CLASSIC_SELECTOR = f"System.Devices.Aep.ProtocolId:=\"{CLASSIC_PROTOCOL_ID}\""

BATTERY_PKEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"
CONNECTED_PKEY = "{83DA6326-97A6-4088-9453-A1923F573B29} 10"

GATT_BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
GATT_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"


class BluetoothDevice:
    def __init__(self, name, address, kind="Unknown", raw_obj=None):
        self.name = name if name else "Unknown"
        self.address = address
        self.kind = kind
        self.rssi = -100
        self.raw = raw_obj

        self.battery = None
        self.battery_left = None
        self.battery_right = None
        self.battery_case = None

        self.is_connected = False
        self.is_paired = False
        self.ble_device = None  # GATT instance

        if raw_obj and hasattr(raw_obj, "properties"):
            raw_batt = raw_obj.properties.get(BATTERY_PKEY)
            base, left, right, case = WindowsBluetoothManager._parse_battery_value(raw_batt)

            self.battery = base
            self.battery_left = left
            self.battery_right = right
            self.battery_case = case

            self.is_connected = raw_obj.properties.get(CONNECTED_PKEY, False)
            if hasattr(raw_obj, "pairing"):
                self.is_paired = raw_obj.pairing.is_paired

    def __repr__(self):
        return f"[{self.kind}] {self.name} ({self.rssi} dBm)"


class WindowsBluetoothManager:
    def __init__(self):
        self.found_devices: Dict[str, BluetoothDevice] = {}
        self._setup_watchers()

    # ==========================================================================================
    # Watchers
    # ==========================================================================================
    def _setup_watchers(self):
        self.classic_watcher = DeviceInformation.create_watcher(
            CLASSIC_SELECTOR,
            [BATTERY_PKEY, CONNECTED_PKEY],
            DeviceInformationKind.ASSOCIATION_ENDPOINT,
        )
        self.classic_watcher.add_added(self._on_classic_added)
        self.classic_watcher.add_updated(self._on_classic_updated)

        self.ble_watcher = BluetoothLEAdvertisementWatcher()
        self.ble_watcher.scanning_mode = BluetoothLEScanningMode.ACTIVE
        self.ble_watcher.add_received(self._on_ble_received)

    def _on_classic_added(self, watcher, device_info):
        self.found_devices[device_info.id] = BluetoothDevice(
            name=device_info.name,
            address=device_info.id,
            kind="Classic",
            raw_obj=device_info,
        )

    def _on_classic_updated(self, watcher, update_info):
        if update_info.id in self.found_devices:
            if CONNECTED_PKEY in update_info.properties:
                self.found_devices[update_info.id].is_connected = update_info.properties[CONNECTED_PKEY]

    def _on_ble_received(self, watcher, event_args):
        addr = f"{event_args.bluetooth_address:012X}"
        name = event_args.advertisement.local_name
        if not name:
            return

        if addr in self.found_devices and self.found_devices[addr].kind == "BLE":
            self.found_devices[addr].rssi = event_args.raw_signal_strength_in_d_bm
        else:
            self.found_devices[addr] = BluetoothDevice(name, addr, "BLE")
            self.found_devices[addr].rssi = event_args.raw_signal_strength_in_d_bm

    async def scan_devices(self, duration=5.0) -> List[BluetoothDevice]:
        self.found_devices.clear()
        self.classic_watcher.start()
        self.ble_watcher.start()
        await asyncio.sleep(duration)
        self.classic_watcher.stop()
        self.ble_watcher.stop()
        return list(self.found_devices.values())

    # ==========================================================================================
    # Battery Value Parser (handles multi-values)
    # ==========================================================================================
    @staticmethod
    def _parse_battery_value(raw):
        if raw is None:
            return (None, None, None, None)

        if isinstance(raw, int) or hasattr(raw, "value"):
            v = int(str(raw))
            return (v, v, None, None)

        txt = str(raw).replace("\r", " ").replace("\n", " ").replace("%", "")
        parts = [p.strip() for p in txt.replace(",", " ").split(" ") if p.strip().isdigit()]
        nums = [int(x) for x in parts]

        if not nums:
            return (None, None, None, None)

        if len(nums) == 1:
            return (nums[0], nums[0], None, None)
        if len(nums) == 2:
            return (nums[0], nums[0], nums[1], None)

        return (nums[0], nums[0], nums[1], nums[2])

    # ==========================================================================================
    # Hybrid Battery Resolver (WinRT + PowerShell fallback)
    # ==========================================================================================
    async def get_battery_for_device(self, device: BluetoothDevice) -> Optional[int]:
        print(f"\n   (Searching battery for '{device.name}')")

        try:
            results = await DeviceInformation.find_all_async(
                "", [BATTERY_PKEY], DeviceInformationKind.DEVICE
            )

            target = None
            if "-" in device.address:
                target = device.address.split("-")[-1].replace(":", "").upper()

            for res in results:
                if (target and target in res.id.upper()) or (
                    res.name and device.name.lower() in res.name.lower()
                ):
                    raw = res.properties.get(BATTERY_PKEY)
                    base, left, right, case = WindowsBluetoothManager._parse_battery_value(raw)
                    if base is not None:
                        device.battery = base
                        device.battery_left = left
                        device.battery_right = right
                        device.battery_case = case
                        return base

        except Exception:
            pass

        print("   → WinRT failed. Trying PowerShell fallback...")

        ps = f"""
        Get-PnpDevice -FriendlyName "*{device.name}*" |
        Get-PnpDeviceProperty -KeyName '{BATTERY_PKEY}' |
        Where-Object {{ $_.Type -ne "Empty" }} |
        Select-Object -ExpandProperty Data
        """

        result = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True)
        data = (result.stdout or "").strip()
        if not data:
            return None

        base, left, right, case = WindowsBluetoothManager._parse_battery_value(data)
        device.battery = base
        device.battery_left = left
        device.battery_right = right
        device.battery_case = case
        return base

    # ==========================================================================================
    # NEW: GATT Live Battery Streaming (Auto Updates)
    # ==========================================================================================
    async def start_gatt_battery_stream(self, device: BluetoothDevice):
        print(f"   (Attempting GATT battery streaming for {device.name})")

        try:
            addr_int = int(device.address, 16)
            device.ble_device = await BluetoothLEDevice.from_bluetooth_address_async(addr_int)
            if not device.ble_device:
                print("   (GATT connect failed)")
                return

            services_result = await device.ble_device.get_gatt_services_async()
            for service in services_result.services:
                if str(service.uuid).lower() == GATT_BATTERY_SERVICE:
                    print("   → GATT Battery Service found")
                    chars_result = await service.get_characteristics_async()

                    for c in chars_result.characteristics:
                        if str(c.uuid).lower() == GATT_BATTERY_LEVEL:
                            print("   → GATT Battery characteristic subscribing")
                            c.add_value_changed(self._on_gatt_battery_changed)
                            status = await c.read_value_async()

                            if status.status == GattCommunicationStatus.SUCCESS:
                                level = int.from_bytes(status.value, "little")
                                device.battery = level
                                print(f"   🔋 Initial GATT Battery: {level}%")
                            return
        except Exception as e:
            print("   (Error starting GATT stream)", e)

    def _on_gatt_battery_changed(self, sender: GattCharacteristic, args):
        try:
            level = int.from_bytes(args.characteristic_value, "little")
            print(f"\n 🔔 Live GATT Battery Update: {level}%")
        except Exception as e:
            print("   (Error parsing GATT value)", e)


    # ==========================================================================================
    # Pair / Unpair
    # ==========================================================================================
    async def pair_device(self, device: BluetoothDevice) -> bool:
        print(f"Pairing {device.name}...")
        if device.is_paired:
            return True

        def handler(sender, args):
            try: args.accept()
            except: pass

        token = device.raw.pairing.custom.add_pairing_requested(handler)
        try:
            result = await device.raw.pairing.custom.pair_async(
                DevicePairingKinds.CONFIRM_ONLY,
                DevicePairingProtectionLevel.DEFAULT,
            )
            device.raw.pairing.custom.remove_pairing_requested(token)

            return result.status == DevicePairingResultStatus.PAIRED

        except Exception as e:
            print("Pair failed", e)
            return False

    async def unpair_device(self, device: BluetoothDevice):
        if not device.is_paired:
            return
        result = await device.raw.pairing.unpair_async()
        print("Unpair result:", result.status)
