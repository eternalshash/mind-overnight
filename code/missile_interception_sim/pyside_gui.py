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
        self.playback_layout.addWidget(self.pause_btn)
        self.playback_layout.addWidget(self.reset_btn)
        
        # --- Telemetry HUD ---
        self.hud_group = QGroupBox("Live Telemetry")
        self.hud_layout = QVBoxLayout(self.hud_group)
        self.sidebar_layout.addWidget(self.hud_group)
        self.hud_active_threats = QLabel("Active Threats: 0")
        self.hud_interceptors = QLabel("Airborne Interceptors: 0")
        self.hud_layout.addWidget(self.hud_active_threats)
        self.hud_layout.addWidget(self.hud_interceptors)
        
        # Main Map Area
        from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
        self.map_view = QGraphicsView()
        self.map_scene = QGraphicsScene()
        self.map_view.setScene(self.map_scene)
        self.map_view.setSceneRect(-896, -640, 1792, 1280)  # full stitched tile mosaic (7x5 tiles of 256px)
        self.map_view.setBackgroundBrush(Qt.black)
        self.map_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.map_view.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.map_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.map_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.map_view.wheelEvent = self.map_wheel
        self._press_pos = None
        self._dragged = False
        self.map_view.mousePressEvent = self.map_mouse_press
        self.map_view.mouseMoveEvent = self.map_mouse_move
        self.map_view.mouseReleaseEvent = self.map_mouse_release
        self.splitter.addWidget(self.map_view)
        
        # Load Background Tiles
        import tile_manager
        z = 4
        center_x, center_y = tile_manager.deg2num(23.5, 120.0, z) # Indo-Pacific
        for dx in range(-3, 4):
            for dy in range(-2, 3):
                pixmap = tile_manager.get_carto_tile(z, center_x + dx, center_y + dy)
                if pixmap:
                    item = QGraphicsPixmapItem(pixmap)
                    item.setPos(dx * 256 - 128, dy * 256 - 128)
                    item.setZValue(-100) # Keep in background
                    self.map_scene.addItem(item)
        
        self.splitter.setSizes([350, 850])
        
        # --- Placement Mode ---
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self.placement_group = QGroupBox("Map Placement Mode")
        self.placement_layout = QHBoxLayout(self.placement_group)
        self.sidebar_layout.insertWidget(0, self.placement_group)
        
        self.mode_btn_group = QButtonGroup(self)
        self.radio_defender = QRadioButton("Place Defender")
        self.radio_defender.setChecked(True)
        self.radio_attacker = QRadioButton("Place Launch Site")
        
        self.mode_btn_group.addButton(self.radio_defender, 0)
        self.mode_btn_group.addButton(self.radio_attacker, 1)
        self.placement_layout.addWidget(self.radio_defender)
        self.placement_layout.addWidget(self.radio_attacker)
        
        self.mode_btn_group.buttonClicked.connect(self.change_placement_mode)
        self.placement_mode = "Defender"
        
        # --- Simulation Engine State ---
        self.sim_time = 0.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.is_playing = False
        
        # Data Structures
        self.waves_schedule = []
        self.active_threats = []
        self.active_interceptors = []
        self.defense_batteries = []
        self.launch_sites = []
        self.transient_items = []
        self.radar_range = 70  # px, shared by the drawn dome and the detection check
        
        self.connect_signals()

    def track(self, item):
        """Register a short-lived scene item so reset can remove it."""
        self.transient_items.append(item)
        return item

    def safe_remove(self, item):
        """Remove an item from the scene if it is still there."""
        if item is not None and item.scene() is self.map_scene:
            self.map_scene.removeItem(item)

    def connect_signals(self):
        self.play_btn.clicked.connect(self.play_sim)
        self.pause_btn.clicked.connect(self.pause_sim)
        self.reset_btn.clicked.connect(self.reset_sim)
        self.add_wave_btn.clicked.connect(self.add_wave)
        
    @Slot()
    def change_placement_mode(self):
        if self.radio_defender.isChecked():
            self.placement_mode = "Defender"
        else:
            self.placement_mode = "Attacker"

    def map_wheel(self, event):
        """Zoom toward the cursor, clamped between 'whole map fits the view' and 6x."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.map_view.transform().m11()
        vp = self.map_view.viewport()
        min_scale = max(vp.width() / 1792, vp.height() / 1280)
        new_scale = max(min_scale, min(6.0, current * factor))
        self.map_view.scale(new_scale / current, new_scale / current)

    def map_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragged = False

    def map_mouse_move(self, event):
        """Left-drag pans the map by scrolling the (hidden) scrollbars."""
        if self._press_pos is None or not (event.buttons() & Qt.LeftButton):
            return
        pos = event.position().toPoint()
        delta = pos - self._press_pos
        if self._dragged or delta.manhattanLength() > 5:  # small jitter still counts as a click
            self._dragged = True
            self.map_view.horizontalScrollBar().setValue(self.map_view.horizontalScrollBar().value() - delta.x())
            self.map_view.verticalScrollBar().setValue(self.map_view.verticalScrollBar().value() - delta.y())
            self._press_pos = pos
            self.map_view.viewport().setCursor(Qt.ClosedHandCursor)

    def map_mouse_release(self, event):
        self.map_view.viewport().unsetCursor()
        if event.button() == Qt.LeftButton and self._press_pos is not None and not self._dragged:
            self.map_clicked(event)  # a clean click places a site/battery
        self._press_pos = None

    def map_clicked(self, event):
        if self.is_playing: return
        scene_pos = self.map_view.mapToScene(event.position().toPoint())
        
        from PySide6.QtGui import QBrush, QPen, QColor
        from PySide6.QtWidgets import QGraphicsEllipseItem
        
        if self.placement_mode == "Defender":
            # Draw radar dome
            r = self.radar_range
            dome = self.map_scene.addEllipse(-r, -r, 2 * r, 2 * r, QPen(QColor(0, 150, 255, 100)), QBrush(QColor(0, 150, 255, 30)))
            dome.setPos(scene_pos)
            # Draw battery core
            core = self.map_scene.addEllipse(-2.5, -2.5, 5, 5, QPen(Qt.NoPen), QBrush(Qt.blue))
            core.setPos(scene_pos)
            self.defense_batteries.append({"x": scene_pos.x(), "y": scene_pos.y(), "dome": dome, "core": core})
        
        elif self.placement_mode == "Attacker":
            # Draw launch site
            site = self.map_scene.addEllipse(-5, -5, 10, 10, QPen(Qt.NoPen), QBrush(Qt.darkRed))
            site.setPos(scene_pos)
            self.launch_sites.append({"x": scene_pos.x(), "y": scene_pos.y(), "item": site})
        
    @Slot()
    def play_sim(self):
        self.is_playing = True
        self.timer.start(50)  # 50 ms loop = 20 fps
        
    @Slot()
    def pause_sim(self):
        self.is_playing = False
        self.timer.stop()
        
    @Slot()
    def reset_sim(self):
        self.pause_sim()
        self.sim_time = 0.0
        for item in self.transient_items:
            self.safe_remove(item)
        self.transient_items.clear()
        self.active_threats.clear()
        self.active_interceptors.clear()
        for wave in self.waves_schedule:
            wave["launched"] = False
            wave["spawned"] = 0
            wave["last_spawn"] = -99
        self.update_hud()
        
    @Slot()
    def add_wave(self):
        delay = self.wave_delay_spin.value()
        wtype = self.wave_type_combo.currentText()
        count = self.wave_count_spin.value()
        
        self.waves_schedule.append({"delay": delay, "type": wtype, "count": count, "launched": False})
        
        row = self.waves_table.rowCount()
        self.waves_table.insertRow(row)
        self.waves_table.setItem(row, 0, QTableWidgetItem(f"{delay:.1f}"))
        self.waves_table.setItem(row, 1, QTableWidgetItem(wtype))
        self.waves_table.setItem(row, 2, QTableWidgetItem(str(count)))
        
