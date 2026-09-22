import numpy as np
import matplotlib.pyplot as plt
import os

def galaxy_ring_stress_test(base_arr, fee_reduction_pct):
    stressed_arr = base_arr * (1 - fee_reduction_pct)
    valuation_impact = stressed_arr * 10 # 10x multiple
    return stressed_arr, valuation_impact

def b2b_moat_scoring():
