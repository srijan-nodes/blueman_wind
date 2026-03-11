import asyncio
import sys
import platform
from win_bluetooth import WindowsBluetoothManager

# Non-blocking input wrapper
async def ainput(prompt: str = "") -> str:
    print(prompt, end="", flush=True)
    return await asyncio.get_event_loop().run_in_executor(
        None, sys.stdin.readline
    )

async def select_device(devices: list, prompt: str):
    if not devices:
        print("No matching devices found.")
        return None
    
    # Sort by RSSI (Signal Strength) so strongest devices are at top
    devices.sort(key=lambda x: x.rssi, reverse=True)

    print(f"\n{'IDX':<4} | {'TYPE':<7} | {'RSSI':<5} | {'BATT':<5} | {'NAME'}")
    print("-" * 60)
    for i, dev in enumerate(devices):
        batt = f"{dev.battery}%" if dev.battery is not None else "--"
        print(f" {i:<4} | {dev.kind:<7} | {dev.rssi:<5} | {batt:<5} | {dev.name}")
    print("-" * 60)
    
    try:
        line = await ainput(f"{prompt} (index): ")
        if not line.strip(): return None
        idx = int(line.strip())
        if 0 <= idx < len(devices):
            return devices[idx]
        return None
    except ValueError:
        return None

# ... (imports and helper functions remain the same) ...

async def main_cli():
    if platform.system() != "Windows":
        print("This tool requires Windows 10/11.")
        return

    manager = WindowsBluetoothManager()
    last_scan_results = []

    print("\n--- BluMan Hybrid (Classic + BLE) ---")
    print("Commands: (s)can, (p)air, (u)npair, (b)attery, (q)uit") # Added (b)attery

    while True:
        line = await ainput("\nAction > ")
        action = line.strip().lower()

        if action == 's':
            print("Scanning for 5 seconds (Classic + BLE)...")
            last_scan_results = await manager.scan_devices(duration=5.0)
            await select_device(last_scan_results, "Select to view details")

        elif action == 'p':
            if not last_scan_results:
                print("Cache empty. Scanning first...")
                last_scan_results = await manager.scan_devices(3.0)
            
            candidates = [d for d in last_scan_results 
                          if d.kind == "Classic" and not d.is_paired]
            
            target = await select_device(candidates, "Select Classic Device to PAIR")
            if target:
                await manager.pair_device(target)

        elif action == 'u':
            print("Fetching paired devices...")
            all_devs = await manager.scan_devices(2.0) 
            paired = [d for d in all_devs if d.is_paired]
            target = await select_device(paired, "Select device to UNPAIR")
            if target:
                await manager.unpair_device(target)

        # --- NEW BATTERY COMMAND ---
        elif action == 'b':
            print("Fetching list of known devices...")
            # 1. Get list of paired/connected devices
            all_devs = await manager.scan_devices(2.0)
            # Filter for likely candidates (Paired Classic or Connected BLE)
            candidates = [d for d in all_devs if d.is_paired or d.is_connected]
            
            target = await select_device(candidates, "Select device to check BATTERY")
            
            if target:
                print(f"Checking battery for {target.name}...")
                lvl = await manager.get_battery_for_device(target)
                
                if lvl is not None:
                    print(f"🔋 Battery Level: {lvl}%")
                else:
                    print("⚠️  Battery level unavailable.")
                    print("   (Ensure device is CONNECTED to Windows and playing audio/active)")

        elif action == 'q':
            break

if __name__ == "__main__":
    try:
        asyncio.run(main_cli())
    except KeyboardInterrupt:
        pass