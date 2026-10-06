import sys
import json
import math
import random
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QSplitter, QGroupBox, QSlider
)
from PySide6.QtCore import Qt, QTimer, Slot, Signal

QUASI_BALLISTIC = "Quasi-Ballistic (Iskander-M)"
# Motion/visual profile per threat archetype (px/s speeds, RGB colour, weave in px at weave_hz).
DEFAULT_PROFILE = {"speed": (80, 150), "color": (255, 0, 0), "radius": 3, "weave_amp": 0, "weave_hz": 0, "weave_start": 0}
THREAT_PROFILES = {
    QUASI_BALLISTIC: {"speed": (170, 210), "color": (255, 70, 220), "radius": 4, "weave_amp": 14, "weave_hz": 1.5, "weave_start": 0.4},
}
INTERCEPTOR_PROFILES = {
    "Patriot PAC-3": {"speed": 220, "color": (0, 255, 255)},
    "THAAD": {"speed": 350, "color": (255, 200, 0)},
    "SM-3": {"speed": 400, "color": (100, 255, 100)},
    "Iron Dome": {"speed": 160, "color": (200, 200, 255)},
}

class DefenseSimulatorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Multi-Wave Tactical Missile Interception Simulator")
        self.resize(1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Splitter to separate sidebar and map
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Sidebar for Controls and Telemetry
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar.setMaximumWidth(400)
        self.splitter.addWidget(self.sidebar)
        
        # --- Wave Builder Panel ---
        self.wave_group = QGroupBox("Wave Builder")
        self.wave_layout = QVBoxLayout(self.wave_group)
        self.sidebar_layout.addWidget(self.wave_group)
        
        self.wave_type_combo = QComboBox()
        self.wave_type_combo.addItems(["Exo-Atmospheric Ballistic", QUASI_BALLISTIC, "Hypersonic Weave", "Low-Altitude Cruise", "Loitering Drone Swarm"])
        self.wave_layout.addWidget(QLabel("Threat Archetype:"))
        self.wave_layout.addWidget(self.wave_type_combo)
        
        self.wave_count_spin = QSpinBox()
        self.wave_count_spin.setRange(1, 1000)
        self.wave_count_spin.setValue(10)
        self.wave_layout.addWidget(QLabel("Missile Count:"))
        self.wave_layout.addWidget(self.wave_count_spin)
        
        self.wave_delay_spin = QDoubleSpinBox()
        self.wave_delay_spin.setRange(0.0, 3600.0)
        self.wave_delay_spin.setValue(0.0)
        self.wave_layout.addWidget(QLabel("Launch Delay (seconds):"))
        self.wave_layout.addWidget(self.wave_delay_spin)
        
        self.add_wave_btn = QPushButton("Add Wave to Schedule")
        self.wave_layout.addWidget(self.add_wave_btn)
        
        self.waves_table = QTableWidget(0, 3)
        self.waves_table.setHorizontalHeaderLabels(["Delay (s)", "Type", "Count"])
        self.wave_layout.addWidget(self.waves_table)
        
        # --- Defense Fleet Configurator ---
        self.fleet_group = QGroupBox("Defense Fleet")
        self.fleet_layout = QVBoxLayout(self.fleet_group)
        self.sidebar_layout.addWidget(self.fleet_group)
        
        self.interceptor_combo = QComboBox()
        self.interceptor_combo.addItems(["Auto (Layered Defense)", "Patriot PAC-3", "THAAD", "SM-3", "Iron Dome"])
        self.fleet_layout.addWidget(QLabel("Interceptor Type:"))
        self.fleet_layout.addWidget(self.interceptor_combo)

        
        self.theater_combo = QComboBox()
        self.theater_combo.addItems(["Indo-Pacific", "Baltic / Eastern Europe", "Middle East"])
        self.fleet_layout.addWidget(QLabel("Theater Preset:"))
        self.fleet_layout.addWidget(self.theater_combo)
        
        # --- Playback Controls ---
        self.playback_group = QGroupBox("Playback")
        self.playback_layout = QHBoxLayout(self.playback_group)
        self.sidebar_layout.addWidget(self.playback_group)
        
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.reset_btn = QPushButton("Reset")
        self.playback_layout.addWidget(self.play_btn)
