import asyncio
from bleak import BleakClient

TARGET_MAC = "4F:99:7B:BC:28:32"  # Update if needed

async def main():
    try:
        print("Connecting GATT...")
        async with BleakClient(TARGET_MAC) as client:
            print("Connected:", client.is_connected)

            if not client.is_connected:
                return

            services = client.services  # service collection
            print("\nEnumerating services...\n")

            # list container .services
            all_services = services.services
            print("Service count:", len(all_services))

            for s in all_services:
                print(f"Service: {s.uuid}")
                for char in s.characteristics:
                    print(f"  Characteristic: {char.uuid}")

    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
