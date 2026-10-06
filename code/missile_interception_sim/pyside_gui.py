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
        
    def update_hud(self):
        active_t = sum(1 for t in self.active_threats if t.get("active", True))
        active_i = sum(1 for i in self.active_interceptors if i.get("active", True))
        self.hud_active_threats.setText(f"Active Threats: {active_t}")
        self.hud_interceptors.setText(f"Airborne Interceptors: {active_i}")
        
    def update_simulation(self):
        self.sim_time += 0.05
        
        # Check for waves to launch sequentially
        for wave in self.waves_schedule:
            if self.sim_time >= wave["delay"] and wave.get("spawned", 0) < wave["count"]:
                if self.sim_time - wave.get("last_spawn", -99) >= 0.4:  # spawn every 0.4s
                    self.launch_single_threat(wave)
                    wave["spawned"] = wave.get("spawned", 0) + 1
                    wave["last_spawn"] = self.sim_time
                
        # Basic Kinematics for Threats
        from PySide6.QtWidgets import QGraphicsLineItem
        from PySide6.QtGui import QPen, QColor
        
        for threat in self.active_threats:
            if not threat.get("active", True): continue
            
            old_x, old_y = threat["x"], threat["y"]
            # Straight-line base flight path
            threat["bx"] += threat["vx"] * 0.05
            threat["by"] += threat["vy"] * 0.05
            threat["age"] += 0.05
            remaining = math.hypot(threat["target_x"] - threat["bx"], threat["target_y"] - threat["by"])
            # Terminal weave: lateral sine offset over the last part of the flight, fading to 0 at the target
            offset = 0.0
            if threat["weave_amp"] and remaining < threat["total"] * threat["weave_start"]:
                offset = threat["weave_amp"] * math.sin(2 * math.pi * threat["weave_hz"] * threat["age"]) * min(1.0, remaining / 40.0)
            speed = math.hypot(threat["vx"], threat["vy"]) or 1.0
            threat["x"] = threat["bx"] - (threat["vy"] / speed) * offset
            threat["y"] = threat["by"] + (threat["vx"] / speed) * offset
            threat["item"].setPos(threat["x"], threat["y"])
            
            # Draw dashed trailing line in the threat's colour
            dash_pen = QPen(QColor(*threat["color"], 150))
            dash_pen.setStyle(Qt.DashLine)
            dash_pen.setWidth(2)
            trail = self.track(self.map_scene.addLine(old_x, old_y, threat["x"], threat["y"], dash_pen))
            trail.setZValue(-10)
            
            # Threat reached its target: it hits (leak) and is removed
            if remaining <= speed * 0.05:
                threat["active"] = False
                self.safe_remove(threat["item"])
                self.draw_impact_marker(threat["target_x"], threat["target_y"])
                continue
            
            # Check radar detection & launch interceptor
            if not threat.get("engaged", False):
                for battery in self.defense_batteries:
                    dist_to_battery = math.hypot(threat["x"] - battery["x"], threat["y"] - battery["y"])
                    if dist_to_battery < self.radar_range:
                        self.launch_interceptor(battery, threat)
                        threat["engaged"] = True
                        break
                            
        # Basic Kinematics for Interceptors
        for interceptor in self.active_interceptors:
            self.update_interceptor_kinematics(interceptor)
            
        self.update_hud()
        
    def launch_single_threat(self, wave):
        from PySide6.QtWidgets import QGraphicsEllipseItem
        from PySide6.QtGui import QBrush, QPen, QColor
        
        # Pick a random launch site, or use default if none exist
        if self.launch_sites:
            site = random.choice(self.launch_sites)
            start_x, start_y = site["x"], site["y"]
        else:
            start_x, start_y = -350, random.uniform(-200, 200)
            
        # Pick a random target (defense battery), or use default
        if self.defense_batteries:
            target = random.choice(self.defense_batteries)
            tx, ty = target["x"], target["y"]
        else:
            tx, ty = 350, random.uniform(-200, 200)
                
        profile = THREAT_PROFILES.get(wave["type"], DEFAULT_PROFILE)
        dx, dy = tx - start_x, ty - start_y
        dist = math.hypot(dx, dy)
        speed = random.uniform(*profile["speed"])
        vx = (dx / dist) * speed if dist > 0 else speed
        vy = (dy / dist) * speed if dist > 0 else 0
        
        r = profile["radius"]
        item = self.track(self.map_scene.addEllipse(-r, -r, 2 * r, 2 * r, QPen(Qt.NoPen), QBrush(QColor(*profile["color"]))))
        item.setPos(start_x, start_y)
        threat = {"x": start_x, "y": start_y, "vx": vx, "vy": vy, "item": item, "target_x": tx, "target_y": ty, "active": True,
                  "bx": start_x, "by": start_y, "total": dist, "age": 0.0, "color": profile["color"],
                  "weave_amp": profile["weave_amp"], "weave_hz": profile["weave_hz"], "weave_start": profile["weave_start"],
                  "type": wave["type"]}
        self.active_threats.append(threat)
            
    def launch_interceptor(self, battery, threat):
        from PySide6.QtWidgets import QGraphicsEllipseItem
        from PySide6.QtGui import QBrush, QPen, QColor
        
        itype = self.interceptor_combo.currentText()
        if itype == "Auto (Layered Defense)":
            if threat.get("type") == QUASI_BALLISTIC or threat.get("type") == "Exo-Atmospheric Ballistic":
                itype = "THAAD"
            elif threat.get("type") == "Loitering Drone Swarm":
                itype = "Iron Dome"
            else:
                itype = "Patriot PAC-3"
                
        profile = INTERCEPTOR_PROFILES.get(itype, INTERCEPTOR_PROFILES["Patriot PAC-3"])
        
        item = self.track(self.map_scene.addEllipse(-2, -2, 4, 4, QPen(Qt.NoPen), QBrush(QColor(*profile["color"]))))
        item.setPos(battery["x"], battery["y"])
        interceptor = {
            "x": battery["x"], "y": battery["y"], 
            "item": item, "target": threat, "speed": profile["speed"], "active": True,
            "color": profile["color"]
        }
        self.active_interceptors.append(interceptor)
        
    def draw_kill_marker(self, x, y):
        """Permanent red X at the intercept point plus a short yellow flash."""
        from PySide6.QtGui import QBrush, QPen, QColor
        x_pen = QPen(QColor(255, 40, 40))
        x_pen.setWidth(3)
        for a, b in (((-7, -7), (7, 7)), ((-7, 7), (7, -7))):
            seg = self.track(self.map_scene.addLine(x + a[0], y + a[1], x + b[0], y + b[1], x_pen))
            seg.setZValue(20)
        flash = self.track(self.map_scene.addEllipse(-14, -14, 28, 28, QPen(Qt.NoPen), QBrush(QColor(255, 220, 0, 170))))
        flash.setPos(x, y)
        flash.setZValue(19)
        QTimer.singleShot(350, lambda: self.safe_remove(flash))

    def draw_impact_marker(self, x, y):
        """Orange burst where a threat got through and hit its target."""
        from PySide6.QtGui import QBrush, QPen, QColor
        burst = self.track(self.map_scene.addEllipse(-12, -12, 24, 24, QPen(QColor(255, 140, 0), 2), QBrush(QColor(255, 100, 0, 140))))
        burst.setPos(x, y)
        burst.setZValue(19)

    def update_interceptor_kinematics(self, interceptor):
        if not interceptor["active"]: return
        
        target = interceptor["target"]
        if not target["active"]:
            interceptor["active"] = False
            self.safe_remove(interceptor["item"])
            return
            
        dx, dy = target["x"] - interceptor["x"], target["y"] - interceptor["y"]
        dist = math.hypot(dx, dy)
        step = interceptor["speed"] * 0.05
        
        if dist <= max(6.0, step): # Interception Hit (radius covers one full step, no overshoot)
            interceptor["active"] = False
            target["active"] = False
            self.safe_remove(interceptor["item"])
            self.safe_remove(target["item"])
            self.draw_kill_marker(target["x"], target["y"])
            return
            
        old_x, old_y = interceptor["x"], interceptor["y"]
        interceptor["x"] += (dx / dist) * step
        interceptor["y"] += (dy / dist) * step
        interceptor["item"].setPos(interceptor["x"], interceptor["y"])
        
        # Interceptor trail
        from PySide6.QtGui import QPen, QColor
        color_tuple = interceptor.get("color", (0, 255, 255))
        int_pen = QPen(QColor(color_tuple[0], color_tuple[1], color_tuple[2], 150))
        int_pen.setStyle(Qt.DashLine)
        int_pen.setWidth(2)
        trail = self.track(self.map_scene.addLine(old_x, old_y, interceptor["x"], interceptor["y"], int_pen))
        trail.setZValue(-10)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DefenseSimulatorMainWindow()
    window.show()
    sys.exit(app.exec())
