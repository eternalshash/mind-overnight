import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_hardware_economics(asp=399, bom_margin=0.40):
    bom_cost = asp * (1 - bom_margin)
    gross_profit = asp - bom_cost
    return bom_cost, gross_profit

def calculate_saas_economics(monthly_fee=5.99, margin=0.85, months=36):
    arr = monthly_fee * 12
    ltv = arr * margin * (months / 12)
    return arr, ltv

def cohort_retention(initial_users, monthly_churn=0.03, months=36):
