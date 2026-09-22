import re
import matplotlib.pyplot as plt
import os
import seaborn as sns
import numpy as np

def scrape_and_parse_reviews():
    # Mocking NLP output for Tech Reviews
    sources = ['The Verge', 'Wired', 'DC Rainmaker', 'Bloomberg']
    aspects = ['Hardware', 'Subscription Paywall', 'Biometrics', 'Ecosystem']
    sentiment_scores = np.random.uniform(-1, 1, (len(sources), len(aspects)))
    return sources, aspects, sentiment_scores

def plot_sentiment_matrix(sources, aspects, scores):
    plt.figure(figsize=(8,6))
