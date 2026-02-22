# US–Iran Strike Probability Dashboard

Real-time Streamlit dashboard tracking market-implied probability of US military strikes on Iran using Polymarket event data. Computes full discrete time distribution (PMF, CDF, Survival, Hazard) and overlays live news flow.

---

## Overview

- **Data Source**: Polymarket Gamma API (`us-strikes-iran-by` event slug).
- **Refresh Rate**: 25 seconds (auto rerun).
- **Deadline**: 2026-06-30 23:59:59 UTC.
- **News Feed**: Google News RSS query (`Trump Iran military strike`).

Pipeline:

1. Fetch event markets.
2. Extract "Yes" outcome prices.
3. Parse date labels → discrete time grid.
4. Sort chronologically.
5. Derive distribution metrics.
6. Render probability structure + liquidity diagnostics.

---

## Distribution Construction

Let:

- \( t_i \) = ordered target dates  
- \( F(t_i) \) = cumulative probability (CDF) from market  
- \( p_i \) = probability mass at \( t_i \) (PMF)  
- \( S(t_i) \) = survival probability  
- \( h(t_i) \) = hazard rate  

### 1. CDF

Directly from market-implied “Yes” probability:

\[
F(t_i) = \text{price}_{Yes}(t_i)
\]

\[
F_{pct}(t_i) = 100 \cdot F(t_i)
\]

---

### 2. PMF (Discrete Mass)

First node:

\[
p_1 = F(t_1)
\]

Recursive difference:

\[
p_i = F(t_i) - F(t_{i-1})
\]

Clipped at zero:

\[
p_i = \max(0, p_i)
\]

\[
p_{pct}(t_i) = 100 \cdot p_i
\]

Interpretation: incremental probability assigned specifically to that date bucket.

---

### 3. Survival Function

\[
S(t_i) = 1 - F(t_i)
\]

\[
S_{pct}(t_i) = 100 \cdot S(t_i)
\]

Probability event has **not** occurred by \( t_i \).

---

### 4. Hazard Rate

First node:

\[
h(t_1) = p_1
\]

Recursive definition:

\[
h(t_i) = 
\begin{cases}
\frac{p_i}{S(t_{i-1})}, & S(t_{i-1}) > 0.001 \\
0, & \text{otherwise}
\end{cases}
\]

\[
h_{pct}(t_i) = 100 \cdot h(t_i)
\]

Interpretation: conditional probability of occurrence at \( t_i \) given survival until \( t_{i-1} \).

---

## Dashboard Panels

### Top Metrics

- Peak Cumulative Risk (max CDF)
- Total Volume
- Total Liquidity
- Average Bid–Ask Spread

Risk Classification:

| Max CDF | Label     |
|---------|----------|
| ≥ 50%   | HIGH     |
| ≥ 20%   | ELEVATED |
| < 20%   | LOW      |

---

### Main Graphs

1. **PMF (Bar)** — Marginal probability mass per date  
2. **CDF (Line + Area)** — Accumulated probability  
3. **Survival (Line)** — Remaining probability  
4. **Hazard (Bar)** — Conditional event intensity  

All rendered with Plotly (dark theme).

---

### Raw Market Matrix

Columns:

| Target Date | CDF (%) | PMF (%) | Survival (%) | Hazard (%) | Volume ($) | Spread |
|-------------|----------|----------|---------------|-------------|------------|--------|

Displays rounded values, sorted chronologically.

---

### Volume Intelligence

Derived metrics:

Let:

- \( V_i \) = volume at node \( i \)
- \( V_{tot} = \sum_i V_i \)

Capital concentration:

\[
\text{Concentration} = \frac{\max(V_i)}{V_{tot}} \cdot 100
\]

Identifies:

- Highest deployed capital date  
- Highest marginal risk node  
- Average spread (proxy for conviction)

---

### Live News Feed

- Google RSS pull (cached 120s).
- Sorted by publication time.
- Displays relative time since publication.

---

## Architecture

| Layer | Function |
|-------|----------|
| Data | Polymarket Gamma API |
| Parsing | JSON decode + fallback eval |
| Time Grid | Date string normalization → datetime |
| Math | Discrete difference operators |
| UI | Streamlit + Plotly |
| Styling | Custom CSS (JetBrains Mono, dark system theme) |
| Refresh | `time.sleep(25)` → `st.rerun()` |

---

## Run

```bash
pip install streamlit requests pandas plotly feedparser
streamlit run app.py
```

---

## Dependencies

- `streamlit`
- `requests`
- `pandas`
- `plotly`
- `feedparser`

---

## Limitations

- Depends on Polymarket event structure stability.
- Assumes monotonic CDF across date buckets.
- Date parsing limited to common month formats.
- No smoothing between discrete nodes.
- News query is keyword-based, not semantic-filtered.
- Hazard unstable if survival approaches zero.
