import asyncio
from bleak import BleakScanner, BleakClient

async def connect_to(device):
    print(f"\nAttempting GATT connect to {device.name} at {device.address}")
    try:
        async with BleakClient(device) as client:
            print("CONNECTED:", client.is_connected)

            if client.is_connected:
                services = client.services.services
                print("Service count:", len(services))
                for s in services:
                    print("Service:", s.uuid)
                    for char in s.characteristics:
                        print("  Characteristic:", char.uuid)
    except Exception as e:
        print("CONNECT ERROR:", e)

async def detection_callback(device, adv_data):
    if device.name and "OnePlus" in device.name:
        print(f"\nFOUND OnePlus ADV -> {device.address}  Connectable={adv_data.connectable}")
        if adv_data.connectable:
            await connect_to(device)

async def main():
    scanner = BleakScanner(detection_callback)
    print("Scanning...")
    await scanner.start()
    await asyncio.sleep(20)
    await scanner.stop()

asyncio.run(main())
