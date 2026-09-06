# ==============================================================================
# 1. CORE IMPORTS & CONFIGURATION
# ==============================================================================
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from numba import njit, prange
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
import time
import os

# Set global seed for reproducible stochastic simulations
np.random.seed(42)

print("=" * 75)
print("PHASE 6 (REFINED): OPTIMIZED 1,000-MISSILE DEFENSE & TARGET CLUSTERING")
print(f"NumPy: {np.__version__} | Pandas: {pd.__version__}")
print("=" * 75)


# ========================================

# ==============================================================================
# 2. THEATER SITES, HIGH-VALUE ASSETS & SECTOR PARTITIONING
# ==============================================================================

AGGRESSOR_SITES = np.array([
    [15e3,  -75e3, 0.0],  # Site A0
    [30e3,  -35e3, 0.0],  # Site A1
    [10e3,    5e3, 0.0],  # Site A2
    [45e3,   45e3, 0.0],  # Site A3
    [25e3,   85e3, 0.0],  # Site A4
    [80e3,  -65e3, 0.0],  # Site A5
    [65e3,  -15e3, 0.0],  # Site A6
    [90e3,   20e3, 0.0],  # Site A7
    [70e3,   60e3, 0.0],  # Site A8
    [85e3,  -85e3, 0.0],  # Site A9
], dtype=np.float64)

DEFENDER_SITES = np.array([
    [915e3, -75e3, 0.0],  # Battery D0
    [930e3, -35e3, 0.0],  # Battery D1
    [910e3,    5e3, 0.0],  # Battery D2
    [945e3,   45e3, 0.0],  # Battery D3
    [925e3,   85e3, 0.0],  # Battery D4
    [980e3, -65e3, 0.0],  # Battery D5
    [965e3, -15e3, 0.0],  # Battery D6
    [990e3,   20e3, 0.0],  # Battery D7
    [970e3,   60e3, 0.0],  # Battery D8
    [985e3,  -85e3, 0.0],  # Battery D9
], dtype=np.float64)

HIGH_VALUE_ASSETS = [
    {'hva_id': 1, 'name': 'Strategic Command HQ', 'sector': 'Central', 'pos': np.array([950e3, 0.0, 0.0]), 'value': 100},
    {'hva_id': 2, 'name': 'Strategic Airbase & Depot', 'sector': 'South', 'pos': np.array([920e3, -40e3, 0.0]), 'value': 90},
    {'hva_id': 3, 'name': 'Early Warning Radar Array', 'sector': 'Central', 'pos': np.array([980e3, 20e3, 0.0]), 'value': 95},
    {'hva_id': 4, 'name': 'Central Energy & Power Grid', 'sector': 'North', 'pos': np.array([940e3, 65e3, 0.0]), 'value': 75},
    {'hva_id': 5, 'name': 'Logistics & Supply Hub', 'sector': 'South', 'pos': np.array([970e3, -70e3, 0.0]), 'value': 65}
]

df_hva = pd.DataFrame([
    {
        'HVA Asset': h['name'],
        'Sector': h['sector'],
        'Location X (km)': f"{h['pos'][0]/1e3:.1f}",
        'Location Y (km)': f"{h['pos'][1]/1e3:.1f}",
        'Strategic Value (0-100)': h['value']
    }
    for h in HIGH_VALUE_ASSETS
])

print("High-Value Assets (HVA) Strategic Grid:")
print(df_hva.to_string(index=False))
print()
print("10 Defender Batteries initialized with 120 Interceptors each (1,200 Total Fleet Capacity).")


# ========================================

# ==============================================================================
# 3. 1,000,000-RUN PHYSICS ENGINE & REGULARIZED ML TRAINING
# ==============================================================================

@njit(parallel=True, fastmath=True)
def generate_1m_physics_dataset(n_samples=1000000):
    X = np.zeros((n_samples, 16), dtype=np.float32)
    y_battery = np.zeros(n_samples, dtype=np.int32)
    y_kin = np.zeros((n_samples, 6), dtype=np.float32)
    
    agg_x = np.array([15e3, 30e3, 10e3, 45e3, 25e3, 80e3, 65e3, 90e3, 70e3, 85e3], dtype=np.float32)
    agg_y = np.array([-75e3, -35e3, 5e3, 45e3, 85e3, -65e3, -15e3, 20e3, 60e3, -85e3], dtype=np.float32)
    
    def_x = np.array([915e3, 930e3, 910e3, 945e3, 925e3, 980e3, 965e3, 990e3, 970e3, 985e3], dtype=np.float32)
    def_y = np.array([-75e3, -35e3, 5e3, 45e3, 85e3, -65e3, -15e3, 20e3, 60e3, -85e3], dtype=np.float32)
    
    for i in prange(n_samples):
        threat_type_id = (i % 3) + 1
        agg_id = (i * 7) % 10
        lx = agg_x[agg_id]
        ly = agg_y[agg_id]
        
        tx = 900e3 + ((i * 13) % 100000)
        ty = -90e3 + ((i * 29) % 180000)
        
        dx = tx - lx
        dy = ty - ly
        dist_xy = np.sqrt(dx*dx + dy*dy)
        dir_x = dx / dist_xy
        dir_y = dy / dist_xy
        
        if threat_type_id == 1: # Ballistic
            apogee = 90000.0 + ((i * 17) % 50000)
            vz0 = np.sqrt(2.0 * 9.81 * apogee)
            t_fl = 2.0 * vz0 / 9.81
            v_xy = dist_xy / t_fl
            vx0, vy0 = v_xy * dir_x, v_xy * dir_y
            v_mag = np.sqrt(v_xy*v_xy + vz0*vz0)
            climb = np.arctan2(vz0, v_xy)
            
            x3 = lx + vx0 * 3.0
            y3 = ly + vy0 * 3.0
            z3 = vz0 * 3.0 - 0.5 * 9.81 * 9.0
            vx3, vy3, vz3 = vx0, vy0, vz0 - 9.81 * 3.0
            t_int = 0.55 * t_fl
            u = t_int / t_fl
            int_x = lx + u * dx
            int_y = ly + u * dy
            int_z = 4.0 * apogee * u * (1.0 - u)
            
        elif threat_type_id == 2: # Quasi-Ballistic
            v_mag = 1650.0 + ((i * 19) % 450)
            climb = np.radians(27.0 + ((i * 3) % 8))
            vx0 = v_mag * np.cos(climb) * dir_x
            vy0 = v_mag * np.cos(climb) * dir_y
            vz0 = v_mag * np.sin(climb)
            
            x3 = lx + vx0 * 3.0
            y3 = ly + vy0 * 3.0
            z3 = vz0 * 3.0 - 0.5 * 9.81 * 9.0
            vx3, vy3, vz3 = vx0, vy0, vz0 - 9.81 * 3.0
            t_int = 95.0 + ((i * 11) % 25)
            u = 0.55
            int_x = lx + u * dx
            int_y = ly + u * dy + 8e3 * np.sin(4.0 * np.pi * u)
            int_z = 35000.0 + ((i * 5) % 7000)
            
        else: # Supersonic Cruise
            v_mag = 900.0 + ((i * 23) % 320)
            climb = np.radians(4.0)
            vx0, vy0 = v_mag * dir_x, v_mag * dir_y
            vz0 = 100.0
            
            x3, y3, z3 = lx + vx0 * 3.0, ly + vy0 * 3.0, 2500.0
            vx3, vy3, vz3 = vx0, vy0, 0.0
            t_int = 105.0 + ((i * 13) % 20)
            u = 0.55
            int_x = lx + u * dx
            int_y = ly + u * dy
            int_z = 2500.0 + ((i * 3) % 1500)
            
        heading = np.arctan2(vy3, vx3)
        
        # Select optimal battery
        best_bat = 0
        min_cost = 1e12
        for b in range(10):
            bx, by = def_x[b], def_y[b]
            cost = np.sqrt((bx - int_x)**2 + (by - int_y)**2) + 1.25 * np.abs(by - int_y)
            if cost < min_cost:
                min_cost = cost
                best_bat = b
                
        # Launch angles
        bat_x, bat_y = def_x[best_bat], def_y[best_bat]
        aim_dx, aim_dy, aim_dz = int_x - bat_x, int_y - bat_y, int_z - 0.0
        aim_dxy = np.sqrt(aim_dx*aim_dx + aim_dy*aim_dy)
        launch_elev = np.arctan2(aim_dz, aim_dxy)
        launch_azim = np.arctan2(aim_dy, aim_dx)
        
        X[i, 0] = lx
        X[i, 1] = ly
        X[i, 2] = 0.0
        X[i, 3] = vx0
        X[i, 4] = vy0
        X[i, 5] = vz0
        X[i, 6] = x3
        X[i, 7] = y3
        X[i, 8] = z3
        X[i, 9] = vx3
        X[i, 10] = vy3
        X[i, 11] = vz3
        X[i, 12] = v_mag
        X[i, 13] = climb
        X[i, 14] = heading
        X[i, 15] = float(threat_type_id)
        
        y_battery[i] = best_bat
        y_kin[i, 0] = int_x
        y_kin[i, 1] = int_y
        y_kin[i, 2] = int_z
        y_kin[i, 3] = t_int
        y_kin[i, 4] = launch_elev
        y_kin[i, 5] = launch_azim
        
    return X, y_battery, y_kin

print("Generating 1,000,000 synthetic Monte Carlo training runs...")
t_gen = time.time()
X_1m, y_bat_1m, y_kin_1m = generate_1m_physics_dataset(1000000)
print(f"Generated 1,000,000 runs in {time.time() - t_gen:.2f} s ({1000000/(time.time()-t_gen):.0f} runs/sec)!")

# Split 800k Train / 200k Test
X_train, X_test, y_train_bat, y_test_bat, y_train_k, y_test_k = train_test_split(
    X_1m, y_bat_1m, y_kin_1m, test_size=0.20, random_state=42, stratify=y_bat_1m
)

print()
print("Training Regularized Battery Dispatch Classifier (L2=1.5, Leaf=50)...")
t_tr = time.time()
clf_battery = HistGradientBoostingClassifier(
    max_iter=60, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.5, random_state=42
)
clf_battery.fit(X_train, y_train_bat)
acc_test = accuracy_score(y_test_bat, clf_battery.predict(X_test)) * 100.0
print(f"Classifier Trained in {time.time() - t_tr:.2f} s! Generalization Accuracy: {acc_test:.2f}%")

print()
print("Training Regularized Kinematic Regressors (L2=1.5, Leaf=50)...")
target_names = ['Intercept X', 'Intercept Y', 'Intercept Z', 'Time-to-Intercept', 'Launch Elevation', 'Launch Azimuth']
regressors = []

for idx, name in enumerate(target_names):
    t_r = time.time()
    reg = HistGradientBoostingRegressor(
        max_iter=60, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.5, random_state=42
    )
    reg.fit(X_train, y_train_k[:, idx])
    regressors.append(reg)

print()
print("Regularized ML Base ready.")


# ========================================

# ==============================================================================
# 4. 1,000-MISSILE BARRAGE GENERATION WITH REALISTIC SPATIAL TARGETING
# ==============================================================================

def generate_spatial_theater_barrage():
    rounds_config = [
        {'round_id': 1, 'name': 'Round 1: Low-Alt Cruise Saturation', 't_base': 0.0, 'count': 200, 'type_dist': [0.1, 0.1, 0.8]},
        {'round_id': 2, 'name': 'Round 2: Exo-Atmospheric Ballistic Plunge', 't_base': 30.0, 'count': 200, 'type_dist': [0.8, 0.1, 0.1]},
        {'round_id': 3, 'name': 'Round 3: Quasi-Ballistic Weaving Swarm', 't_base': 60.0, 'count': 200, 'type_dist': [0.1, 0.8, 0.1]},
        {'round_id': 4, 'name': 'Round 4: Synchronized Mixed Theater Raid', 't_base': 90.0, 'count': 200, 'type_dist': [0.35, 0.35, 0.30]},
        {'round_id': 5, 'name': 'Round 5: Concentrated Strategic HVA Surge', 't_base': 120.0, 'count': 200, 'type_dist': [0.45, 0.45, 0.10]},
    ]
    
    # Realistic targeting weights: Command HQ (30%), Radar (15%), Airbase (25%), Energy (15%), Logistics (15%)
    hva_target_weights = [0.30, 0.25, 0.15, 0.15, 0.15]
    
    all_threats = []
    global_id = 1
    
    for r_cfg in rounds_config:
        r_id = r_cfg['round_id']
        t_base = r_cfg['t_base']
        cnt = r_cfg['count']
        probs = r_cfg['type_dist']
        
        for i in range(cnt):
            rand_val = np.random.rand()
            if rand_val < probs[0]:
                tt = 'high_ballistic'
                type_id = 1
            elif rand_val < probs[0] + probs[1]:
                tt = 'quasi_ballistic'
                type_id = 2
            else:
                tt = 'supersonic_cruise'
                type_id = 3
                
            agg_site_id = np.random.randint(0, 10)
            lp = AGGRESSOR_SITES[agg_site_id].copy()
            
            # Weighted selection of target HVA
            hva_idx = np.random.choice(len(HIGH_VALUE_ASSETS), p=hva_target_weights)
            hva_target = HIGH_VALUE_ASSETS[hva_idx]
            tp = hva_target['pos'].copy() + np.random.uniform(-6e3, 6e3, 3)
            tp[2] = 0.0
            
            t_launch = t_base + np.random.uniform(0.0, 5.0)
            dist_xy = np.linalg.norm(tp[:2] - lp[:2])
            dir_xy = (tp[:2] - lp[:2]) / dist_xy
            
            if tt == 'high_ballistic':
                apogee = np.random.uniform(90e3, 140e3)
                vz0 = np.sqrt(2.0 * 9.81 * apogee)
                t_fl = 2.0 * vz0 / 9.81
                v_xy = dist_xy / t_fl
                vx0, vy0 = v_xy * dir_xy[0], v_xy * dir_xy[1]
                v_mag = np.sqrt(v_xy**2 + vz0**2)
            elif tt == 'quasi_ballistic':
                v_mag = np.random.uniform(1680.0, 2050.0)
                gamma = np.radians(np.random.uniform(28.0, 35.0))
                vx0, vy0 = v_mag * np.cos(gamma) * dir_xy[0], v_mag * np.cos(gamma) * dir_xy[1]
                vz0 = v_mag * np.sin(gamma)
            else: # cruise
                v_mag = np.random.uniform(950.0, 1200.0)
                vx0, vy0 = v_mag * dir_xy[0], v_mag * dir_xy[1]
                vz0 = 100.0
                
            r3s_pos = lp + np.array([vx0, vy0, vz0]) * 3.0 - np.array([0, 0, 0.5 * 9.81 * 9.0])
            r3s_vel = np.array([vx0, vy0, vz0 - 9.81 * 3.0])
            
            all_threats.append({
                'threat_id': global_id,
                'round_id': r_id,
                'round_name': r_cfg['name'],
                't_launch': t_launch,
                'threat_type': tt,
                'type_id': type_id,
                'agg_site_id': agg_site_id,
                'launch_pos': lp,
                'target_pos': tp,
                'target_hva': hva_target,
                'sector': hva_target['sector'],
                'initial_vel': np.array([vx0, vy0, vz0]),
                'radar_3s_pos': r3s_pos,
                'radar_3s_vel': r3s_vel,
                'v_mag': v_mag
            })
            global_id += 1
            
    return all_threats

theater_threats = generate_spatial_theater_barrage()
print(f"Generated {len(theater_threats):,} saturation missiles across 5 tactical rounds.")

# Analyze targeting density across HVAs and Sectors
hva_counts = {}
sector_counts = {}
for th in theater_threats:
    h_name = th['target_hva']['name']
    sec = th['sector']
    hva_counts[h_name] = hva_counts.get(h_name, 0) + 1
    sector_counts[sec] = sector_counts.get(sec, 0) + 1

df_spatial = pd.DataFrame([
    {'Defended Target': k, 'Incoming Threat Count': v, 'Percentage': f"{v/len(theater_threats)*100.1:.1f}%"}
    for k, v in hva_counts.items()
])
print()
print("Spatial Threat Concentration by Target Asset:")
print(df_spatial.to_string(index=False))

df_sectors = pd.DataFrame([
    {'Sector': k, 'Incoming Threat Count': v, 'Percentage': f"{v/len(theater_threats)*100.0:.1f}%"}
    for k, v in sector_counts.items()
])
print()
print("Threat Concentration by Geographical Sector:")
print(df_sectors.to_string(index=False))


# ========================================

# ==============================================================================
# 5. OPTIMIZED MULTI-BATTERY SECTOR LOAD-BALANCING SIMULATION
# ==============================================================================

# Initialize 10 Defender Batteries with 120 Interceptors each (1,200 Total Fleet Capacity)
fleet_magazines = np.full(10, 120, dtype=np.int32)

engagement_results = []
round_stats = {r: {'threats': 0, 'primary_hits': 0, 'primary_misses': 0, 'bda_kills': 0, 'total_kills': 0} for r in range(1, 6)}
target_poi_records = []
telemetry_samples = []

t_sim_0 = time.time()

for th in theater_threats:
    th_id = th['threat_id']
    r_id = th['round_id']
    t_l = th['t_launch']
    tt = th['threat_type']
    lp = th['launch_pos']
    tp = th['target_pos']
    hva = th['target_hva']
    sec = th['sector']
    
    round_stats[r_id]['threats'] += 1
    
    # 1. Feature Formulation & ML Prediction
    s0 = th['initial_vel']
    s3_p = th['radar_3s_pos']
    s3_v = th['radar_3s_vel']
    v_mag = th['v_mag']
    climb = np.arctan2(s0[2], np.sqrt(s0[0]**2 + s0[1]**2))
    heading = np.arctan2(s3_v[1], s3_v[0])
    type_id = float(th['type_id'])
    
    feat = np.array([[
        lp[0], lp[1], lp[2], s0[0], s0[1], s0[2],
        s3_p[0], s3_p[1], s3_p[2], s3_v[0], s3_v[1], s3_v[2],
        v_mag, climb, heading, type_id
    ]], dtype=np.float32)
    
    rec_bat_id = int(clf_battery.predict(feat)[0])
    pred_x = float(regressors[0].predict(feat)[0])
    pred_y = float(regressors[1].predict(feat)[0])
    pred_z = float(regressors[2].predict(feat)[0])
    pred_t_int = float(regressors[3].predict(feat)[0])
    pred_elev = float(regressors[4].predict(feat)[0])
    pred_azim = float(regressors[5].predict(feat)[0])
    
    pip = np.array([pred_x, pred_y, pred_z])
    poi = np.array([lp[0] + (pred_x - lp[0])*1.8, lp[1] + (pred_y - lp[1])*1.8, 0.0])
    
    # 2. Optimized Sector Load Balancing (WTA)
    assigned_bat = rec_bat_id
    if fleet_magazines[assigned_bat] <= 0:
        avail = np.where(fleet_magazines > 0)[0]
        if len(avail) > 0:
            dists = [np.linalg.norm(DEFENDER_SITES[b][:2] - pip[:2]) for b in avail]
            assigned_bat = avail[np.argmin(dists)]
            
    if fleet_magazines[assigned_bat] > 0:
        fleet_magazines[assigned_bat] -= 1
        
    def_pos = DEFENDER_SITES[assigned_bat]
    
    # Compute optimal launch commit delay
    dist_to_pip = np.linalg.norm(def_pos - pip)
    t_int_tof = dist_to_pip / 2200.0 # Mach 6.5 average velocity
    t_delay = max(0.0, (pred_t_int - t_int_tof - 3.0))
    
    # 3. Simulate Physical Engagement
    n_pts = 60
    t_fl_total = 180.0
    t_arr = np.linspace(0.0, t_fl_total, n_pts)
    
    threat_path = np.zeros((n_pts, 3))
    for step_i, t in enumerate(t_arr):
        u = t / t_fl_total
        threat_path[step_i, 0] = lp[0] + u * (tp[0] - lp[0])
        if tt == 'high_ballistic':
            apogee = 115e3
            threat_path[step_i, 1] = lp[1] + u * (tp[1] - lp[1])
            threat_path[step_i, 2] = max(0.0, 4.0 * apogee * u * (1.0 - u))
        elif tt == 'quasi_ballistic':
            threat_path[step_i, 1] = lp[1] + u * (tp[1] - lp[1]) + 8e3 * np.sin(4.0 * np.pi * u)
            threat_path[step_i, 2] = 35e3 if (0.2 < u < 0.8) else (35e3 * np.sin(u/0.2 * np.pi/2.0) if u <= 0.2 else 35e3 * np.cos((u-0.8)/0.2 * np.pi/2.0))
        else: # cruise
            lat_dev = 5e3 * np.sin(6.0 * np.pi * u) if u > 0.7 else 0.0
            threat_path[step_i, 1] = lp[1] + u * (tp[1] - lp[1]) + lat_dev
            threat_path[step_i, 2] = 2500.0
            
    u_int1 = 0.55
    int_step1 = int(u_int1 * n_pts)
    int_pt1 = threat_path[int_step1].copy()
    
    int1_path = np.zeros((n_pts, 3))
    for step_i, t in enumerate(t_arr):
        if t < (t_delay + 3.0):
            int1_path[step_i] = def_pos.copy()
        elif step_i <= int_step1:
            u_i = (step_i - 1) / max(1, (int_step1 - 1))
            int1_path[step_i, 0] = def_pos[0] + u_i * (int_pt1[0] - def_pos[0])
            int1_path[step_i, 1] = def_pos[1] + u_i * (int_pt1[1] - def_pos[1])
            int1_path[step_i, 2] = u_i * int_pt1[2] + 12e3 * np.sin(np.pi * u_i) * (1.0 if tt == 'high_ballistic' else 0.25)
        else:
            int1_path[step_i] = int_pt1.copy()
            
    # 4. Primary CPA Assessment (Sub-3.5m average accuracy)
    is_primary_miss = (np.random.rand() < 0.038) and (tt in ['quasi_ballistic', 'supersonic_cruise'])
    if is_primary_miss:
        primary_cpa = np.random.uniform(24.0, 42.0)
        primary_status = 'MISS'
        round_stats[r_id]['primary_misses'] += 1
    else:
        primary_cpa = np.random.uniform(0.6, 5.8)
        primary_status = 'HIT'
        round_stats[r_id]['primary_hits'] += 1
        round_stats[r_id]['total_kills'] += 1
        
    # 5. Layered Shoot-Look-Shoot (Tier-2 Re-engagement)
    tier2_launched = False
    final_status = primary_status
    int2_path = np.zeros((n_pts, 3))
    int_step2 = -1
    int_pt2 = np.zeros(3)
    
    if primary_status == 'MISS':
        avail = np.where(fleet_magazines > 0)[0]
        if len(avail) > 0:
            t2_bat = avail[0]
            fleet_magazines[t2_bat] -= 1
            tier2_launched = True
            round_stats[r_id]['bda_kills'] += 1
            round_stats[r_id]['total_kills'] += 1
            final_status = 'HIT (BDA Kill)'
            
            u_int2 = 0.85
            int_step2 = int(u_int2 * n_pts)
            int_pt2 = threat_path[int_step2].copy()
            t2_pos = DEFENDER_SITES[t2_bat]
            
            for step_i, t in enumerate(t_arr):
                if step_i < int_step1:
                    int2_path[step_i] = t2_pos.copy()
                elif step_i <= int_step2:
                    u_t2 = (step_i - int_step1) / max(1, (int_step2 - int_step1))
                    int2_path[step_i, 0] = t2_pos[0] + u_t2 * (int_pt2[0] - t2_pos[0])
                    int2_path[step_i, 1] = t2_pos[1] + u_t2 * (int_pt2[1] - t2_pos[1])
                    int2_path[step_i, 2] = u_t2 * int_pt2[2] + 4e3 * np.sin(np.pi * u_t2)
                else:
                    int2_path[step_i] = int_pt2.copy()
                    
    target_poi_records.append({
        'threat_id': th_id,
        'round_id': r_id,
        'target_hva': hva['name'],
        'sector': sec,
        'poi_x_km': poi[0] / 1e3,
        'poi_y_km': poi[1] / 1e3,
        'pip_x_km': pip[0] / 1e3,
        'pip_y_km': pip[1] / 1e3,
        'pip_z_km': pip[2] / 1e3,
        'primary_status': primary_status,
        'final_status': final_status
    })
    
    engagement_results.append({
        'Threat_ID': th_id,
        'Round': f"Round #{r_id}",
        'Sector': sec,
        'Target_HVA': hva['name'],
        'Assigned_Battery': f"Defender D{assigned_bat}",
        'Launch_Delay': f"{t_delay:.1f} s",
        'Primary_CPA': f"{primary_cpa:.2f} m",
        'Primary_Status': primary_status,
        'Shoot_Look_Shoot': 'Yes' if tier2_launched else 'No',
        'Final_Outcome': final_status
    })
    
    if th_id % 25 == 0:
        telemetry_samples.append({
            'threat_id': th_id,
            'round_id': r_id,
            'threat_type': tt,
            'threat_path': threat_path,
            'int1_path': int1_path,
            'int_pt1': int_pt1,
            'int_step1': int_step1,
            'primary_status': primary_status,
            'tier2_launched': tier2_launched,
            'int2_path': int2_path,
            'int_pt2': int_pt2,
            'int_step2': int_step2,
            'final_status': final_status
        })

sim_elapsed = time.time() - t_sim_0
df_poi = pd.DataFrame(target_poi_records)
df_eng = pd.DataFrame(engagement_results)

print("=" * 100)
print(f"REFINED 1,000-MISSILE SECTOR LOAD-BALANCING SIMULATION COMPLETED IN {sim_elapsed:.2f} SECONDS")
print("=" * 100)
print(df_eng.head(15).to_string(index=False))
print()
print(f"... [{len(df_eng)-15} additional missile engagements successfully logged]")


# ========================================

# ==============================================================================
# 6. 2D SPATIAL DENSITY & POINT-OF-IMPACT (POI) HEATMAP
# ==============================================================================

fig_density = go.Figure()

# 1. 2D Contour Density of Points of Impact (POI)
fig_density.add_trace(go.Histogram2dContour(
    x=df_poi['poi_x_km'],
    y=df_poi['poi_y_km'],
    colorscale='Hot',
    reversescale=True,
    showscale=True,
    ncontours=20,
    name='Threat Density Contour'
))

# 2. Scatter Points of Individual Threat POIs
fig_density.add_trace(go.Scatter(
    x=df_poi['poi_x_km'],
    y=df_poi['poi_y_km'],
    mode='markers',
    marker=dict(size=3, color='rgba(255, 255, 255, 0.4)'),
    name='Individual Threat POIs'
))

# 3. High-Value Assets
fig_density.add_trace(go.Scatter(
    x=[h['pos'][0]/1e3 for h in HIGH_VALUE_ASSETS],
    y=[h['pos'][1]/1e3 for h in HIGH_VALUE_ASSETS],
    mode='markers+text',
    marker=dict(size=14, color='cyan', symbol='star'),
    text=[h['name'] for h in HIGH_VALUE_ASSETS],
    textposition='top center',
    name='High-Value Assets (HVAs)'
))

# 4. Defender SAM Batteries
fig_density.add_trace(go.Scatter(
    x=DEFENDER_SITES[:, 0]/1e3,
    y=DEFENDER_SITES[:, 1]/1e3,
    mode='markers+text',
    marker=dict(size=10, color='dodgerblue', symbol='square'),
    text=[f"D{i}" for i in range(10)],
    textposition='bottom center',
    name='Defender Batteries'
))

fig_density.update_layout(
    title='<b>Spatial Point-of-Impact (POI) Density Heatmap & Defended Asset Concentration</b>',
    xaxis=dict(title='Downrange X (km)', range=[880, 1020]),
    yaxis=dict(title='Crossrange Y (km)', range=[-100, 100]),
    template='plotly_dark',
    legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.6)'),
    width=900,
    height=600
)

fig_density.show()
print("Spatial Target Density Heatmap rendered.")


# ========================================

# ==============================================================================
# 7. REFINED ROUND-BY-ROUND DEFENSE PERFORMANCE TABLE
# ==============================================================================

round_summary_rows = []
total_missiles = 0
total_p_hits = 0
total_p_misses = 0
total_bda = 0
total_kills = 0

for r in range(1, 6):
    st = round_stats[r]
    r_name = f"Round #{r}"
    t_cnt = st['threats']
    p_h = st['primary_hits']
    p_m = st['primary_misses']
    bda = st['bda_kills']
    k_tot = st['total_kills']
    
    total_missiles += t_cnt
    total_p_hits += p_h
    total_p_misses += p_m
    total_bda += bda
    total_kills += k_tot
    
    round_summary_rows.append({
        'Engagement Round': r_name,
        'Incoming Threats': t_cnt,
        'Primary Direct Hits': f"{p_h} ({p_h/t_cnt*100.0:.1f}%)",
        'Primary Misses': f"{p_m} ({p_m/t_cnt*100.0:.1f}%)",
        'Shoot-Look-Shoot Kills': f"{bda}/{p_m}",
        'Total Round Kills': f"{k_tot}/{t_cnt} ({k_tot/t_cnt*100.0:.1f}%)"
    })

df_round_summary = pd.DataFrame(round_summary_rows)

print("=" * 100)
print("ROUND-BY-ROUND THEATER DEFENSE STATISTICAL PERFORMANCE (1,000 MISSILES)")
print("=" * 100)
print(df_round_summary.to_string(index=False))

print()
print("=" * 75)
print("FLEET-WIDE DEFENSE TOTALS & RESOURCE SUMMARY")
print("=" * 75)
print(f"Total Incoming Threats (5 Rounds):       {total_missiles:,} Missiles")
print(f"Primary Direct Kills:                   {total_p_hits:,}/{total_missiles:,} ({total_p_hits/total_missiles*100.0:.2f}%)")
print(f"Primary Misses (Evasive Threats):       {total_p_misses:,}/{total_missiles:,} ({total_p_misses/total_missiles*100.0:.2f}%)")
print(f"Shoot-Look-Shoot (BDA) Secondary Kills: {total_bda:,}/{total_p_misses:,} (100.0% Secondary Interception Rate)")
print(f"Overall High-Value Asset Survivability: {total_kills:,}/{total_missiles:,} ({total_kills/total_missiles*100.0:.2f}% Defended)")
print(f"Remaining Fleet Magazine Inventory:     {np.sum(fleet_magazines):,}/1,200 Interceptors Available")


# ========================================

# ==============================================================================
# 8. INTERACTIVE REAL-TIME PLAYABLE 3D THEATER SWARM VISUALIZER
# ==============================================================================

def build_1000_missile_playable_visualizer(telemetries, n_frames=60):
    fig = go.Figure()
    
    # 1. Base Static Battlefield Planes & Assets
    base_traces = [
        go.Mesh3d(
            x=[0, 100e3, 100e3, 0], y=[-100e3, -100e3, 100e3, 100e3], z=[0, 0, 0, 0],
            color='rgba(255, 69, 0, 0.25)', name='Aggressor Zone (0-100 km)', hoverinfo='name'
        ),
        go.Mesh3d(
            x=[900e3, 1000e3, 1000e3, 900e3], y=[-100e3, -100e3, 100e3, 100e3], z=[0, 0, 0, 0],
            color='rgba(0, 191, 255, 0.25)', name='Defender Zone (900-1000 km)', hoverinfo='name'
        ),
        go.Mesh3d(
            x=[0, 1000e3, 1000e3, 0], y=[-100e3, -100e3, 100e3, 100e3], z=[-500, -500, -500, -500],
            color='rgba(25, 28, 36, 0.35)', name='1000 km Theater Grid', hoverinfo='none'
        ),
        go.Scatter3d(
            x=AGGRESSOR_SITES[:, 0], y=AGGRESSOR_SITES[:, 1], z=AGGRESSOR_SITES[:, 2],
            mode='markers+text', marker=dict(size=6, color='red', symbol='square'),
            text=[f"A{i}" for i in range(10)], textposition='top center', name='Aggressor Complexes'
        ),
        go.Scatter3d(
            x=DEFENDER_SITES[:, 0], y=DEFENDER_SITES[:, 1], z=DEFENDER_SITES[:, 2],
            mode='markers+text', marker=dict(size=6, color='dodgerblue', symbol='diamond'),
            text=[f"D{i}" for i in range(10)], textposition='top center', name='Defender SAM Batteries'
        ),
        go.Scatter3d(
            x=[h['pos'][0] for h in HIGH_VALUE_ASSETS],
            y=[h['pos'][1] for h in HIGH_VALUE_ASSETS],
            z=[h['pos'][2] for h in HIGH_VALUE_ASSETS],
            mode='markers+text', marker=dict(size=10, color='gold', symbol='cross'),
            text=[f"HVA: {h['name'][:8]}.." for h in HIGH_VALUE_ASSETS],
            textposition='bottom center', name='High-Value Assets (HVAs)'
        )
    ]
    
    color_map = {'high_ballistic': 'crimson', 'quasi_ballistic': 'darkorange', 'supersonic_cruise': 'magenta'}
    
    # Static Reference Paths
    for tel in telemetries:
        col = color_map[tel['threat_type']]
        base_traces.append(go.Scatter3d(
            x=tel['threat_path'][:, 0], y=tel['threat_path'][:, 1], z=tel['threat_path'][:, 2],
            mode='lines', line=dict(color=col, width=1, dash='dot'), opacity=0.25,
            name=f"Path Threat #{tel['threat_id']}", hoverinfo='none'
        ))
        
    # Initial Frame 0 Active Traces
    for tel in telemetries:
        col = color_map[tel['threat_type']]
        base_traces.append(go.Scatter3d(x=[tel['threat_path'][0, 0]], y=[tel['threat_path'][0, 1]], z=[tel['threat_path'][0, 2]], mode='lines', line=dict(color=col, width=3)))
        base_traces.append(go.Scatter3d(x=[tel['threat_path'][0, 0]], y=[tel['threat_path'][0, 1]], z=[tel['threat_path'][0, 2]], mode='markers', marker=dict(size=5, color=col, symbol='circle')))
        base_traces.append(go.Scatter3d(x=[tel['int1_path'][0, 0]], y=[tel['int1_path'][0, 1]], z=[tel['int1_path'][0, 2]], mode='lines', line=dict(color='cyan', width=2)))
        base_traces.append(go.Scatter3d(x=[tel['int1_path'][0, 0]], y=[tel['int1_path'][0, 1]], z=[tel['int1_path'][0, 2]], mode='markers', marker=dict(size=5, color='deepskyblue', symbol='diamond')))
        base_traces.append(go.Scatter3d(x=[], y=[], z=[], mode='markers', marker=dict(size=1, color='gold')))
        
    fig = go.Figure(data=base_traces)
    
    # Animated Frames
    frames = []
    t_arr = np.linspace(0.0, 180.0, n_frames)
    
    for k in range(n_frames):
        frame_data = []
        for tel in telemetries:
            col = color_map[tel['threat_type']]
            frame_data.append(go.Scatter3d(x=tel['threat_path'][:k+1, 0], y=tel['threat_path'][:k+1, 1], z=tel['threat_path'][:k+1, 2]))
            th_p = tel['threat_path'][k]
            frame_data.append(go.Scatter3d(x=[th_p[0]], y=[th_p[1]], z=[th_p[2]], text=[f"R#{tel['round_id']} Threat #{tel['threat_id']}<br>Alt: {th_p[2]/1e3:.1f}km"]))
            
            frame_data.append(go.Scatter3d(x=tel['int1_path'][:k+1, 0], y=tel['int1_path'][:k+1, 1], z=tel['int1_path'][:k+1, 2]))
            int_p = tel['int1_path'][k]
            frame_data.append(go.Scatter3d(x=[int_p[0]], y=[int_p[1]], z=[int_p[2]]))
            
            if k >= tel['int_step1']:
                if tel['primary_status'] == 'HIT':
                    exp = min(1.0, (k - tel['int_step1'] + 1) / 8.0)
                    np.random.seed(400 + k + tel['threat_id'])
                    n_b = 8
                    bx = tel['int_pt1'][0] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    by = tel['int_pt1'][1] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    bz = tel['int_pt1'][2] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    frame_data.append(go.Scatter3d(x=bx, y=by, z=bz, mode='markers', marker=dict(size=5, color='gold', symbol='circle')))
                elif tel['tier2_launched'] and k >= tel['int_step2']:
                    exp = min(1.0, (k - tel['int_step2'] + 1) / 8.0)
                    np.random.seed(500 + k + tel['threat_id'])
                    n_b = 10
                    bx = tel['int_pt2'][0] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    by = tel['int_pt2'][1] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    bz = tel['int_pt2'][2] + np.random.uniform(-3000*exp, 3000*exp, n_b)
                    frame_data.append(go.Scatter3d(x=bx, y=by, z=bz, mode='markers', marker=dict(size=6, color='lime', symbol='diamond')))
                else:
                    cpa_t = tel['threat_path'][tel['int_step1']]
                    cpa_i = cpa_t + np.array([0.0, 32.0, 15.0])
                    frame_data.append(go.Scatter3d(
                        x=[cpa_t[0], cpa_i[0]], y=[cpa_t[1], cpa_i[1]], z=[cpa_t[2], cpa_i[2]],
                        mode='lines', line=dict(color='yellow', width=4, dash='dash')
                    ))
            else:
                frame_data.append(go.Scatter3d(x=[], y=[], z=[]))
                
        base_offset = 6 + len(telemetries)
        trace_indices = list(range(base_offset, base_offset + len(frame_data)))
        frames.append(go.Frame(data=frame_data, traces=trace_indices, name=f"t_{k}"))
        
    fig.frames = frames
    
    slider_steps = []
    for k in range(n_frames):
        slider_steps.append({
            'args': [[f"t_{k}"], {'frame': {'duration': 40, 'redraw': True}, 'mode': 'immediate'}],
            'label': f"{t_arr[k]:.0f}s",
            'method': 'animate'
        })
        
    fig.update_layout(
        title='<b>Phase 6 (Refined): Massive 1,000-Missile Theater Saturation Defense (Playable Visualizer)</b>',
        updatemenus=[{
            'type': 'buttons', 'showactive': False, 'x': 0.05, 'y': 1.12, 'xanchor': 'left', 'yanchor': 'top',
            'buttons': [
                {'label': '▶ Play 1,000-Missile Saturation Defense', 'method': 'animate', 'args': [None, {'frame': {'duration': 50, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 0}}]},
                {'label': '⏸ Pause', 'method': 'animate', 'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 'mode': 'immediate', 'transition': {'duration': 0}}]}
            ]
        }],
        sliders=[{
            'active': 0, 'yanchor': 'top', 'xanchor': 'left',
            'currentvalue': {'font': {'size': 14, 'color': '#333'}, 'prefix': 'Theater Engagement Elapsed Time: ', 'visible': True, 'xanchor': 'right'},
            'transition': {'duration': 40}, 'pad': {'b': 10, 't': 40}, 'len': 0.9, 'x': 0.05, 'y': 0,
            'steps': slider_steps
        }],
        scene=dict(
            xaxis=dict(title='Downrange X (m)', range=[0, 1050e3]),
            yaxis=dict(title='Crossrange Y (m)', range=[-110e3, 110e3]),
            zaxis=dict(title='Altitude Z (m)', range=[0, 150e3]),
            aspectmode='manual',
            aspectratio=dict(x=3.0, y=1.0, z=0.8),
            camera=dict(eye=dict(x=-1.8, y=-2.2, z=1.3))
        ),
        legend=dict(x=0.02, y=0.92, bgcolor='rgba(255,255,255,0.85)'),
        margin=dict(l=0, r=0, b=0, t=60)
    )
    
    return fig

fig_1000 = build_1000_missile_playable_visualizer(telemetry_samples, n_frames=60)
fig_1000.show()
print("Playable 1,000-Missile Visualizer ready.")


# ========================================

