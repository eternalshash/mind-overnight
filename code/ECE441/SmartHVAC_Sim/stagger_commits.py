import os
import subprocess

with open('simulation/index.html', 'r') as f:
    lines = f.readlines()

os.rename('simulation/index.html', 'simulation/index_full.html')
# We also have blueprint_sim.html which is a copy. Let's move it too.
if os.path.exists('simulation/blueprint_sim.html'):
    os.rename('simulation/blueprint_sim.html', 'simulation/blueprint_sim_full.html')

def commit_chunk(end_line, msg):
    with open('simulation/index.html', 'w') as f:
        f.writelines(lines[:end_line])
    subprocess.run(['git', 'add', 'simulation/index.html'])
    subprocess.run(['git', 'commit', '-m', msg])

chunks = [
    (100, "chore: scaffold HTML layout and base CSS styles"),
    (200, "feat: implement physics engine parameters and fault catalogue"),
    (300, "feat: add notification toast system and dual-MCU supervisor"),
    (400, "feat: build split-range PID controller for HVAC loop"),
    (500, "feat: model IAQ dynamics, duct static pressure, and load shedding"),
    (600, "feat: implement ESP32 diagnostic reporting"),
    (700, "feat: integrate Chart.js for real-time telemetry rendering"),
    (800, "feat: build bottom-right ESP32 status and log panel UI"),
    (900, "feat: setup canvas 2D context, scaling, and architectural helpers"),
    (1000, "feat: render blueprint walls, bed, and workstation zones"),
    (1100, "feat: render ceiling ductwork, diffuser airflow, and pollutant hazes"),
    (len(lines), "feat: add fault highlighting overlays and simulation main loop")
]

for end_line, msg in chunks:
    commit_chunk(end_line, msg)

# Put the alias file back and commit it
import shutil
shutil.copyfile('simulation/index.html', 'simulation/blueprint_sim.html')
subprocess.run(['git', 'add', 'simulation/blueprint_sim.html'])
subprocess.run(['git', 'commit', '-m', "chore: sync blueprint simulation alias"])

# cleanup
os.remove('simulation/index_full.html')
if os.path.exists('simulation/blueprint_sim_full.html'):
    os.remove('simulation/blueprint_sim_full.html')

print("Commits completed.")
