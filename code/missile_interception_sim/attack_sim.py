# ==============================================================================
# 1. CORE IMPORTS & CONFIGURATION
# ==============================================================================
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
import time
import os

# Deterministic verification seeds
np.random.seed(42)
torch.manual_seed(42)

print("=" * 80)
print("INTERCONTINENTAL 2,500-MISSILE ATTACK OPTIMIZATION (10,000+ km SCALE, 20,000 RUNS)")
print(f"PyTorch: {torch.__version__} | NumPy: {np.__version__} | Pandas: {pd.__version__}")
print("=" * 80)

# ==============================================================================
# 2. THEATER GEOGRAPHY, LAUNCH SITES & VITAL TARGET ASSETS (>= 10,000 km)
# ==============================================================================
THEATER_X_MAX = 12000e3  # 12,000 km downrange
THEATER_Y_MAX = 10000e3  # 10,000 km crossrange
THEATER_Z_MAX = 1500e3   # 1,500 km exo-atmospheric apogee ceiling

# Aggressor Launch Complexes (Western Sector: 0 - 500 km)
AGGRESSOR_LAUNCH_BASES = np.array([
    [100e3, 1500e3, 0.0],   # Base Alpha
    [250e3, 3500e3, 0.0],   # Base Bravo
    [150e3, 5000e3, 0.0],   # Base Charlie
    [300e3, 6500e3, 0.0],   # Base Delta
    [200e3, 8500e3, 0.0],   # Base Echo
], dtype=np.float32)

# Vital Defending Targets (Far Eastern Sector: >= 10,000 km)
VITAL_TARGETS = [
    {
        'id': 1,
        'name': 'Hardened Missile Silo Alpha',
        'type': 'Missile Silo',
        'x': 10200e3, 'y': 2200e3, 'z': 0.0,
        'radius': 35e3,       # 35 km blast radius tolerance
        'strategic_value': 130.0,
        'vulnerability': 0.85
    },
    {
        'id': 2,
        'name': 'Underground Missile Silo Beta',
        'type': 'Missile Silo',
        'x': 10800e3, 'y': 7800e3, 'z': 0.0,
        'radius': 35e3,
        'strategic_value': 130.0,
        'vulnerability': 0.80
    },
    {
        'id': 3,
        'name': 'Strategic Command & Control HQ',
        'type': 'Command HQ',
        'x': 10500e3, 'y': 5000e3, 'z': 0.0,
        'radius': 45e3,
        'strategic_value': 160.0,
        'vulnerability': 0.70
    },
    {
        'id': 4,
        'name': 'Primary Strategic Airbase Runway',
        'type': 'Military Runway',
        'x': 11200e3, 'y': 3200e3, 'z': 0.0,
        'radius': 50e3,
        'strategic_value': 100.0,
        'vulnerability': 0.90
    },
    {
        'id': 5,
        'name': 'Forward Strategic Airbase North',
        'type': 'Military Runway',
        'x': 11100e3, 'y': 6800e3, 'z': 0.0,
        'radius': 45e3,
        'strategic_value': 95.0,
        'vulnerability': 0.95
    },
    {
        'id': 6,
        'name': 'Early Warning Ballistic Radar Array',
        'type': 'Radar Grid',
        'x': 11500e3, 'y': 8500e3, 'z': 0.0,
        'radius': 30e3,
        'strategic_value': 120.0,
        'vulnerability': 0.95
    }
]

# ==============================================================================
# 3. INTERCONTINENTAL SELF-AIMING SWARM NEURAL NETWORK
# ==============================================================================
class IntercontinentalAttackerSwarm(nn.Module):
    def __init__(self, num_missiles=2500, num_targets=len(VITAL_TARGETS)):
        super().__init__()
        self.num_missiles = num_missiles
        self.num_targets = num_targets
        
        self.target_logits = nn.Parameter(torch.randn(num_missiles, num_targets) * 0.5)
        
        self.refine_net = nn.Sequential(
            nn.Linear(num_targets + 4, 128),
            nn.LeakyReLU(0.1),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.1),
            nn.Linear(64, 4)
        )
        
    def forward(self, target_positions):
        soft_assignments = torch.softmax(self.target_logits, dim=-1)
        base_pois = torch.matmul(soft_assignments, target_positions)
        
        norm_pois = base_pois / THEATER_X_MAX
        features = torch.cat([soft_assignments, norm_pois, torch.sin(norm_pois * np.pi)], dim=-1)
        
        refinements = self.refine_net(features)
        offsets_xy = torch.tanh(refinements[:, :2]) * 20e3
        pois = base_pois + offsets_xy
        
        speeds = 6000.0 + torch.sigmoid(refinements[:, 2]) * 1500.0
        apogees = 600e3 + torch.sigmoid(refinements[:, 3]) * 600e3
        
        return pois, speeds, apogees, soft_assignments

target_coords = torch.tensor([[t['x'], t['y']] for t in VITAL_TARGETS], dtype=torch.float32)
target_values = torch.tensor([t['strategic_value'] for t in VITAL_TARGETS], dtype=torch.float32)
target_radii = torch.tensor([t['radius'] for t in VITAL_TARGETS], dtype=torch.float32)
target_vuln = torch.tensor([t['vulnerability'] for t in VITAL_TARGETS], dtype=torch.float32)

def compute_swarm_loss(pois, soft_assignments, target_coords, target_values, target_radii, target_vuln):
    num_missiles = pois.shape[0]
    diff = pois.unsqueeze(1) - target_coords.unsqueeze(0)
    dist_sq = torch.sum(diff ** 2, dim=-1)
    dist = torch.sqrt(dist_sq + 1e-4)
    
    norm_dist = dist / target_radii.unsqueeze(0)
    assigned_dist_loss = torch.sum(soft_assignments * norm_dist) / num_missiles
    
    hit_prob = torch.sigmoid((1.5 - norm_dist) * 2.0)
    weighted_damage = torch.sum(soft_assignments * hit_prob * (target_values * target_vuln).unsqueeze(0))
    
    target_proportions = torch.mean(soft_assignments, dim=0)
    entropy_reg = -torch.sum(target_proportions * torch.log(target_proportions + 1e-6))
    
    total_loss = assigned_dist_loss - 0.05 * weighted_damage - 0.15 * entropy_reg
    return total_loss, weighted_damage.item(), assigned_dist_loss.item()

def train_attack_sim():
    model = IntercontinentalAttackerSwarm(num_missiles=2500, num_targets=len(VITAL_TARGETS))
    optimizer = optim.Adam(model.parameters(), lr=0.015, weight_decay=1e-5)
    num_runs = 20000
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_runs, eta_min=0.0005)

    print("=" * 80)
    print(f"TRAINING SWARM MODEL OVER {num_runs:,} RUNS (2,500 MISSILES @ 10,000+ km)...")
    print("=" * 80)

    t_start = time.time()
    for run in range(1, num_runs + 1):
        optimizer.zero_grad()
        pois, speeds, apogees, soft_assignments = model(target_coords)
        loss, damage_score, dist_metric = compute_swarm_loss(
            pois, soft_assignments, target_coords, target_values, target_radii, target_vuln
        )
        loss.backward()
        optimizer.step()
        scheduler.step()
        
        if run == 1 or run % 2000 == 0:
            print(f"Run {run:5d}/{num_runs:,} | Loss: {loss.item():.4f} | Normalized Distance: {dist_metric:.3f} | Swarm Damage Score: {damage_score:.1f}")

    t_elapsed = time.time() - t_start
    print("=" * 80)
    print(f"COMPLETED {num_runs:,} RUNS IN {t_elapsed:.2f} SECONDS!")
    print("=" * 80)

    torch.save(model.state_dict(), "attacker_swarm_model.pth")
    print("Saved 'attacker_swarm_model.pth'")

    # Export Plot
    model.eval()
    with torch.no_grad():
        pois, speeds, apogees, soft_assignments = model(target_coords)
        pois_np = pois.numpy()
        assignments_np = soft_assignments.numpy()
        hard_targets = np.argmax(assignments_np, axis=1)

    launch_base_indices = np.random.randint(0, len(AGGRESSOR_LAUNCH_BASES), size=2500)
    launch_positions = AGGRESSOR_LAUNCH_BASES[launch_base_indices]

    plt.figure(figsize=(14, 11), facecolor='#0e1117')
    ax = plt.gca()
    ax.set_facecolor('#0e1117')

    ax.scatter(AGGRESSOR_LAUNCH_BASES[:, 0]/1e3, AGGRESSOR_LAUNCH_BASES[:, 1]/1e3, 
               s=140, c='#ff4444', marker='s', edgecolors='white', linewidths=1.5, label='Aggressor Launch Bases (0-500 km)', zorder=5)

    ax.scatter(pois_np[:, 0]/1e3, pois_np[:, 1]/1e3, 
               s=6, c='#ff7700', alpha=0.6, label='Missile POIs (2,500 Fleet @ 10,000+ km)', zorder=4)

    for t in VITAL_TARGETS:
        circle = plt.Circle((t['x']/1e3, t['y']/1e3), t['radius']/1e3, 
                            color='#00e5ff', fill=True, alpha=0.18, linestyle='--', linewidth=2, zorder=3)
        ax.add_patch(circle)
        ax.scatter(t['x']/1e3, t['y']/1e3, s=160, c='#00e5ff', marker='*', edgecolors='white', zorder=6)
        ax.text(t['x']/1e3, t['y']/1e3 + 200, t['name'], color='#00e5ff', fontsize=9.5, 
                ha='center', weight='bold', zorder=7)

    sample_indices = np.random.choice(2500, size=30, replace=False)
    for idx in sample_indices:
        lp = launch_positions[idx]
        tp = pois_np[idx]
        ax.plot([lp[0]/1e3, tp[0]/1e3], [lp[1]/1e3, tp[1]/1e3], 
                color='#ffaa00', alpha=0.25, linestyle=':', linewidth=1)

    ax.set_title("Self-Guided Attack Simulation: 2,500-Missile Swarm Allocation (Run 20,000 | 10,000+ km Theater)", 
                 fontsize=14, color='white', pad=20, weight='bold')
    ax.set_xlabel("Downrange X Position (km)", fontsize=12, color='white')
    ax.set_ylabel("Crossrange Y Position (km)", fontsize=12, color='white')
    ax.set_xlim(-200, 12200)
    ax.set_ylim(-200, 10200)
    ax.tick_params(colors='white')
    ax.grid(color='#333333', linestyle='--', linewidth=0.7, alpha=0.5)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3, facecolor='#1a1c23', edgecolor='#444444', labelcolor='white', fontsize=10)

    plt.savefig("attack_sim_results.png", dpi=300, bbox_inches='tight', facecolor=plt.gcf().get_facecolor())
    plt.close()
    print("Saved 'attack_sim_results.png'")

if __name__ == "__main__":
    train_attack_sim()
