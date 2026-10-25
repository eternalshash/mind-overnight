#!/bin/bash
# ECE 441 Smart HVAC - Raspberry Pi 5 Automated Edge Server Provisioning
# Installs Mosquitto MQTT broker, paho-mqtt, configures LAN listener on :1883,
# and registers the systemd auto-start service on :8765.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== 1. Installing Mosquitto MQTT Broker & Python MQTT Client ==="
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mosquitto mosquitto-clients python3-paho-mqtt sqlite3

echo "=== 2. Configuring Mosquitto for Local ESP32 LAN Connections (:1883) ==="
sudo tee /etc/mosquitto/conf.d/ece441.conf > /dev/null << 'EOF'
listener 1883 0.0.0.0
allow_anonymous true
EOF
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

echo "=== 3. Installing systemd Service (ece441-hvac-edge.service) ==="
mkdir -p "$PROJECT_DIR/rpi_server/data"
sed "s|/home/pi/SmartHVAC_Sim|$PROJECT_DIR|g; s|User=pi|User=$(whoami)|g" \
    "$SCRIPT_DIR/ece441-hvac-edge.service" | sudo tee /etc/systemd/system/ece441-hvac-edge.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable ece441-hvac-edge.service
sudo systemctl restart ece441-hvac-edge.service

sleep 2
echo "=== 4. Verifying Edge Server Health ==="
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
echo ""
echo "✅ Raspberry Pi 5 Edge Server is LIVE and enabled on boot!"
echo "   LAN Console:  http://$(hostname).local:8765/"
echo "   Digital Twin: http://$(hostname).local:8765/simulation/index.html"
echo "   MQTT Broker:  $(hostname).local:1883"
