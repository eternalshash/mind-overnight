import numpy as np
import matplotlib.pyplot as plt
import os

def galaxy_ring_stress_test(base_arr, fee_reduction_pct):
    stressed_arr = base_arr * (1 - fee_reduction_pct)
    valuation_impact = stressed_arr * 10 # 10x multiple
    return stressed_arr, valuation_impact

def b2b_moat_scoring():
    clinical = 85
    defense = 90
    enterprise = 70
    return (clinical + defense + enterprise) / 3

def plot_moat_radar():
    categories = ['Clinical', 'Defense', 'Enterprise', 'Hardware', 'Software']
    scores = [85, 90, 70, 80, 85]
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    ax.fill(angles, scores, color='blue', alpha=0.25)
    ax.plot(angles, scores, color='blue', linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    plt.title('Moat Radar')
    
    os.makedirs('../charts', exist_ok=True)
    plt.savefig('../charts/moat_radar.png')

if __name__ == '__main__':
    plot_moat_radar()

