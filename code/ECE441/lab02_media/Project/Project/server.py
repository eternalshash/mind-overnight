#!/usr/bin/env python3
# ECE 441 Experiment 2 - UDP listener (server)
# Receives AES-encrypted ADXL345 readings, decrypts them, prints them,
# and draws a live plot of the last 50 samples.

import socket
import sys
import datetime
import matplotlib.pyplot as plot
from matplotlib import animation
from Cryptodome.Cipher import AES

# ---- server network configuration ----
SERVER_IP_ADDRESS = "0.0.0.0"   # listen on all interfaces
PORT = 6000                    # use 6000 on the Illinois Tech campus network
                                # (must match PORTNUMBER in the client)

# ---- AES key and IV (must be identical to KEY and IV in the client, 16 chars) ----
KEY = b'3874460957140850'
iv = b'9331626268227018'

# x-axis positions for the plot and the rolling data buffers (last 50 samples)
time = [0] * 50
for i in range(0, 50):
    time[i] = i

ax_points = [float(0)] * 50
ay_points = [float(0)] * 50
az_points = [float(0)] * 50

print("starting UDP Server Setup")
sys.stdout.flush()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_IP_ADDRESS, PORT))

print("waiting for data to receive")
sys.stdout.flush()

# ---- plot setup ----
fig = plot.figure()
ax = plot.axes(xlim=(0, 50), ylim=(-2, 2))
lineX, lineY, lineZ, = ax.plot([], [], [], [], [], [], lw=2)


def init():
    lineX.set_data([], [])
    lineY.set_data([], [])
    lineZ.set_data([], [])
    return lineX, lineY, lineZ,


def updateData(i):
    # wait for one encrypted packet, then decrypt it
    decryption_suite = AES.new(KEY, AES.MODE_CBC, IV=iv)
    data, addr = sock.recvfrom(64)
    print(''.join('{:02x}'.format(x) for x in data))
    plain_text = decryption_suite.decrypt(data)

    # payload looks like "x, y, z,\n"
    data = plain_text.decode('utf-8')
    ax_val, ay_val, az_val, dump = data.split(",")
    print("ADXL345 X-Axis: " + ax_val + "\tY-Axis: " + ay_val + "\tZ-Axis: " + az_val + "\t"
          + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    sys.stdout.flush()

    # slide the window: drop oldest sample, append newest
    del ax_points[0]
    del ay_points[0]
    del az_points[0]
    ax_points.append(float(ax_val))
    ay_points.append(float(ay_val))
    az_points.append(float(az_val))
    lineX.set_data(time, ax_points)
    lineY.set_data(time, ay_points)
    lineZ.set_data(time, az_points)
    return lineX, lineY, lineZ,


anim = animation.FuncAnimation(fig, updateData, init_func=init,
                               frames=200, interval=20, blit=True)
plot.show()
