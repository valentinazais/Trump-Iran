# US–Iran Strike Probability Dashboard

Real-time Streamlit dashboard tracking market-implied probability of US military strikes on Iran using Polymarket event data. Computes a discrete time distribution (PMF, CDF, Survival, Hazard) and integrates live news flow.

---

## Overview

- **Data Source**: Polymarket Gamma API (`us-strikes-iran-by`)
- **Refresh Rate**: 25 seconds (auto rerun)
- **Deadline**: 2026-06-30 23:59:59 UTC
- **News Feed**: Google News RSS (keyword-based)
- **Output**: Probability term structure + liquidity diagnostics

---

## Distribution Construction

Let:

- \( t_i \) = ordered target dates  
- \( F(t_i) \) = cumulative probability (CDF)  
- \( p_i \) = probability mass (PMF)  
- \( S(t_i) \) = survival probability  
- \( h(t_i) \) = hazard rate  

---

### 1. CDF

\[
F(t_i) = \text{Yes market price at } t_i
\]

\[
F_{\%}(t_i) = 100 \cdot F(t_i)
\]

---

### 2. PMF (Discrete First Difference)

First node:

\[
p_1 = F(t_1)
\]

Recursive definition:

\[
p_i = \max(0,\; F(t_i) - F(t_{i-1}))
\]

\[
p_{\%}(t_i) = 100 \cdot p_i
\]

Interpretation: marginal probability assigned specifically to bucket \( t_i \).

---

### 3. Survival Function

\[
S(t_i) = 1 - F(t_i)
\]

\[
S_{\%}(t_i) = 100 \cdot S(t_i)
\]

Probability event has not occurred by \( t_i \).

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
\frac{p_i}{S(t_{i-1})}, & \text{if } S(t_{i-1}) > 0.001 \\
0, & \text{otherwise}
\end{cases}
\]

\[
h_{\%}(t_i) = 100 \cdot h(t_i)
\]

Interpretation: conditional probability of occurrence at \( t_i \) given survival until \( t_{i-1} \).

---

## Dashboard Components

### Top Metrics

- Peak cumulative risk (max CDF)
- Total volume
- Total liquidity
- Average bid–ask spread

Risk classification:

| Max CDF | Label     |
|----------|-----------|
| ≥ 50%    | HIGH      |
| ≥ 20%    | ELEVATED  |
| < 20%    | LOW       |

---

### Main Charts

- **PMF** — marginal probability per date (bar)
- **CDF** — cumulative probability (line + area)
- **Survival** — remaining probability (line)
- **Hazard** — conditional event intensity (bar)

---

### Raw Market Table

| Column         | Description |
|----------------|------------|
| Target Date    | Event bucket date |
| CDF (%)        | Cumulative probability |
| PMF (%)        | Marginal probability |
| Survival (%)   | 1 − CDF |
| Hazard (%)     | Conditional probability |
| Volume ($)     | Capital deployed |
| Spread         | Bid–ask spread |

---

## Volume Intelligence

Let:

- \( V_i \) = volume at node \( i \)
- \( V_{tot} = \sum_i V_i \)

Capital concentration:

\[
\text{Concentration} = \frac{\max(V_i)}{V_{tot}} \cdot 100
\]

Identifies:

- Date with highest capital deployment
- Date with highest marginal probability (PMF)
- Average spread (liquidity proxy)

---

## Architecture

| Layer        | Function |
|--------------|----------|
| Data         | Polymarket API (JSON) |
| Parsing      | Outcome extraction + date normalization |
| Math         | Discrete differences + conditional ratios |
| UI           | Streamlit |
| Charts       | Plotly (dark theme) |
| Refresh      | `time.sleep(25)` → `st.rerun()` |

---

## Run

```bash
pip install streamlit requests pandas plotly feedparser
streamlit run app.py
