---
name: ipo-analyzer
description: >-
  Methodology and pipeline for conducting Quantitative & Fundamental Analysis on hardware+SaaS hybrid IPOs (like Oura or PSUS).
---

# IPO Analyzer Skill

This skill provides the standard operating procedure (SOP) and pipeline specifications for generating institutional-grade IPO research memorandums and quantitative models. It is highly optimized for Hardware + SaaS hybrid business models (e.g., Oura Health, connected fitness, wearables).

## Pipeline Specifications

When tasked with running an IPO analysis, strictly follow these 5 modules:

### Module 1: Hybrid Unit Economics & Cohort Engine
1. **Segment Hardware vs. Subscription SaaS**:
   - Model the Hardware ASP and Bill of Materials (BOM) gross margin (e.g., 35-45%).
   - Model the hardware replacement cycle (e.g., micro-battery degradation driving a 2.5-3 year upgrade cycle).
   - Model the Subscription SaaS revenue (e.g., monthly/annual fee), high gross margins (80%+), Annual Recurring Revenue (ARR), Net Revenue Retention (NRR), and LTV/CAC ratio.
2. **Attachment Rate**: Estimate the percentage of hardware buyers who retain the subscription after their initial free trial.

### Module 2: Dual-Engine Valuation & Monte Carlo Simulation
1. **Monte Carlo DCF Simulation**:
   - Run 10,000 simulations using stochastic variables such as annual unit growth, monthly subscriber churn, and hardware upgrade intervals.
   - Calculate the Valuation Probability Distribution and extract Bull, Base, and Bear implied enterprise values.
2. **Public Peer Comps Benchmarking**:
   - Compare the target company against a bespoke basket of peers representing hardware resilience, ecosystem lock-in, and clinical-grade recurring revenue.
   - Track multiples: EV/Sales, EV/ARR, Gross Margin, and the Rule of 40.

### Module 3: Financial News & Tech Review NLP Engine
1. **Source Scraping**: Extract sentiment and data from structured tech reviews (The Verge, Wired, DC Rainmaker, etc.) and financial news coverage.
2. **Aspect-Based Classification**:
   - Categorize sentiment into exact product verticals: Hardware & Battery Degradation, Subscription Paywall Backlash, Biometric/Feature Accuracy, and Ecosystem Lock-in.
3. **Strict Entity Matching**: Avoid generic tokens (e.g., avoid "PS" for Pershing Square, use strictly "PSUS" or "Pershing Square" to avoid false positives).

### Module 4: Moat Resilience & Big Tech Threat Modeling
1. **Pricing Stress-Test**: Quantify the impact on ARR and valuation if the company is forced to reduce or eliminate its subscription fee to match a zero-subscription competitor (e.g., Samsung Galaxy Ring).
2. **Historical Lifecycle Comps**: Benchmark against cautionary and successful precedents (e.g., Fitbit's commoditization trap vs. Garmin's sports moat vs. GoPro's peak).
3. **Enterprise Defense**: Score the B2B, Clinical, and Defense Enterprise Contract moat.

### Module 5: Report & Memo Generation
Format the output as a professional 8-10 page investment memo covering:
- Executive Summary & Deal Structure
- Unit Economics & Cohort Retention Analysis
- Peer Comps & Monte Carlo Price Targets (Bull/Base/Bear)
- Strategic Moat & Big Tech Risk Assessment
- NLP Sentiment & Tech Review Matrix
- Final Investment Verdict & Key Monitoring Catalysts.

## Deliverables Structure
Always generate the following when executing this skill:
1. **Code & Visualizations**: Save all Monte Carlo and Python modeling in a centralized `code/` folder or Jupyter Notebook.
2. **High-Quality Research Memorandum**: Generate a clean Markdown (`.md`) and export it to PDF using the defined memo structure.
3. **Charts/Figures**: Save all generated high-res charts (Valuation distribution, Unit Economics Waterfall, Tech Review Sentiment Matrix, Moat Radar) to a `charts/` directory.

