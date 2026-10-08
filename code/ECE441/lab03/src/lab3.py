# lab3.py: ECE 441 Experiment 3 Bluetooth Gateway and ThingSpeak Cloud Client
# Gateway Platform: Raspberry Pi 3 Model B+ (Raspberry Pi OS Linux)
# Function: Reads temperature bytes over RFCOMM Channel 1 and posts to ThingSpeak
# Author: Shashwat Choudhry

import socket
import time
import sys
import thingspeak

# Target HC-06 Bluetooth Transceiver Configuration
bluetooth_addr = "00:14:03:05:5B:F3"  # Verified HC-06 MAC address
bluetooth_port = 1                    # RFCOMM virtual serial port channel 1

# MathWorks ThingSpeak IoT Cloud Configuration
channel_id = 3518177                  # Assigned ThingSpeak Channel ID
write_key = "INYZROAEU08IFDYH"        # Unique 16-character Write API Key
update_url = "https://api.thingspeak.com/update"

print("==================================================")
print("ECE 441 Lab 3: Raspberry Pi IoT Gateway Starting")
print(f"Connecting to Bluetooth Device: {bluetooth_addr} on Channel {bluetooth_port}")
print("==================================================")

# Initialize ThingSpeak Cloud Channel object
ts = thingspeak.Channel(channel_id, write_key, update_url)

# Instantiate Bluetooth RFCOMM socket utilizing Linux BlueZ stack
bluetooth_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

try:
    bluetooth_socket.connect((bluetooth_addr, bluetooth_port))
    print("Bluetooth RFCOMM connection successfully established!")
    print("HC-06 LED should now remain SOLID RED.")
except Exception as e:
    print(f"Failed to establish Bluetooth connection: {e}")
    sys.exit(1)

last_upload_time = 0.0  # Timestamp tracker for 15-second rate limit

try:
    while True:
        # Read incoming byte from Bluetooth socket
        received_data = bluetooth_socket.recv(1)
        if not received_data:
            print("Bluetooth connection closed by remote peer.")
            break
            
        temperature = int.from_bytes(received_data, byteorder='big')
        print("Current Temperature: %d" % temperature)
        
        # Enforce ThingSpeak 15-second update throttle policy
        current_time = time.time()
        if (current_time - last_upload_time) >= 15.0:
            thingspeak_field1 = {"field1": temperature}
            try:
                ts.update(thingspeak_field1)
                print(f"[Upload] Successfully synchronized to ThingSpeak Field 1: {temperature}")
                last_upload_time = current_time
            except Exception as ts_err:
                print(f"ThingSpeak upload error: {ts_err}")
                
except KeyboardInterrupt:
    print("
Keyboard interrupt detected by user. Exiting gracefully...")
except Exception as err:
    print(f"An unexpected runtime error occurred: {err}")
finally:
    bluetooth_socket.close()
    print("Bluetooth RFCOMM socket closed cleanly.")
