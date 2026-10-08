# ble_temperature_client.py: Modern Python BLE GATT Client for Raspberry Pi
# Demonstrates BLE data acquisition using the asynchronous Bleak library
# Author: Shashwat Choudhry

import asyncio
from bleak import BleakScanner, BleakClient

# Standard Bluetooth SIG Assigned UUIDs for Environmental Sensing
ENV_SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
TEMP_CHAR_UUID    = "00002a6e-0000-1000-8000-00805f9b34fb"

def notification_callback(sender: int, data: bytearray):
    """Asynchronous callback invoked when peripheral pushes new temperature data."""
    # Standard GATT 0x2A6E format: signed 16-bit integer, 0.01 degree Celsius resolution
    raw_temp = int.from_bytes(data, byteorder='little', signed=True)
    tempC = raw_temp / 100.0
    tempF = (tempC * 1.8) + 32.0
    print(f"[BLE Push Notification] Temp: {tempC:.2f} C ({tempF:.2f} F)")

async def main():
    print("==================================================")
    print("Scanning for BLE Environmental Sensing Peripherals...")
    print("==================================================")
    
    # Step 1: Asynchronously scan 2.4 GHz BLE advertising channels
    devices = await BleakScanner.discover(timeout=5.0)
    target_device = None
    for d in devices:
        if d.name and "TempSensor" in d.name:
            target_device = d
            break
            
    if not target_device:
        print("Target BLE temperature peripheral not located in advertising scan.")
        return

    print(f"Discovered BLE Device: {target_device.name} [{target_device.address}]")
    
    # Step 2: Establish asynchronous GATT client connection
    async with BleakClient(target_device.address) as client:
        connected = client.is_connected
        print(f"GATT Connection Status: {connected}")
        
        # Step 3: Discover and print GATT services
        services = client.services
        for s in services:
            print(f"Found Service: {s.uuid}")
            
        # Step 4: Enable asynchronous push notifications via CCCD
        print(f"Subscribing to notifications on Characteristic: {TEMP_CHAR_UUID}")
        await client.start_notify(TEMP_CHAR_UUID, notification_callback)
        
        # Maintain event loop while awaiting notifications
        print("Awaiting BLE notifications (Press Ctrl+C to stop)...")
        await asyncio.sleep(60.0)
        
        # Step 5: Clean unsubscribe before disconnecting
        await client.stop_notify(TEMP_CHAR_UUID)

if __name__ == "__main__":
    asyncio.run(main())
