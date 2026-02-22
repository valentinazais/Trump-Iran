# US–Iran Strike Probability Dashboard

Real-time Streamlit dashboard tracking the market-implied probability of US military strikes on Iran using Polymarket event data.  
Constructs a discrete time distribution: PMF, CDF, Survival, and Hazard.

---

## Overview

- **Data Source**: Polymarket Gamma API (`us-strikes-iran-by`)
- **Refresh Rate**: 25 seconds
- **Deadline**: 2026-06-30 23:59:59 UTC
- **News Feed**: Google News RSS (keyword-based)
- **Output**: Probability term structure + liquidity diagnostics

---

# Distribution Construction

Let:

- `t_i` = ordered target dates  
- `F(t_i)` = cumulative probability (CDF)  
- `p_i` = probability mass (PMF)  
- `S(t_i)` = survival probability  
- `h(t_i)` = hazard rate  

---

## 1. Cumulative Distribution Function (CDF)

Definition:

`F(t_i) = Yes market price at t_i`

Percentage form:

`F%(t_i) = 100 × F(t_i)`

Interpretation: probability the event has occurred **on or before** date `t_i`.

---

## 2. Probability Mass Function (PMF)

First node:

`p_1 = F(t_1)`

Recursive difference:

`p_i = max(0, F(t_i) − F(t_{i−1}))`

Percentage form:

`p%(t_i) = 100 × p_i`

Interpretation: marginal probability assigned **specifically** to bucket `t_i`.

---

## 3. Survival Function

Definition:

`S(t_i) = 1 − F(t_i)`

Percentage form:

`S%(t_i) = 100 × S(t_i)`

Interpretation: probability the event has **not** occurred by date `t_i`.

---

## 4. Hazard Rate

First node:

`h(t_1) = p_1`

Recursive definition:

`h(t_i) = p_i / S(t_{i−1})`  if  `S(t_{i−1}) > 0.001`  
`h(t_i) = 0`                 otherwise  

Percentage form:

`h%(t_i) = 100 × h(t_i)`

Interpretation: conditional probability of occurrence at `t_i`  
given survival until `t_{i−1}`.

---

# Dashboard Components

## Top Metrics

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

## Main Charts

- **PMF** — marginal probability per date (bar chart)
- **CDF** — cumulative probability (line + area)
- **Survival** — remaining probability (line)
- **Hazard** — conditional event intensity (bar chart)

---

## Raw Market Table

| Column        | Description |
|---------------|------------|
| Target Date   | Event bucket date |
| CDF (%)       | Cumulative probability |
| PMF (%)       | Marginal probability |
| Survival (%)  | 1 − CDF |
| Hazard (%)    | Conditional probability |
| Volume ($)    | Capital deployed |
| Spread        | Bid–ask spread |

---

# Volume Intelligence

Let:

- `V_i` = volume at node `i`
- `V_tot = sum(V_i)`

Capital concentration:

`Concentration = (max(V_i) / V_tot) × 100`

Identifies:

- Date with highest capital deployment
- Date with highest marginal probability (PMF)
- Average spread (liquidity proxy)

---

# Architecture

| Layer      | Function |
|------------|----------|
| Data       | Polymarket API (JSON) |
| Parsing    | Outcome extraction + date normalization |
| Math       | Discrete first differences + conditional ratios |
| UI         | Streamlit |
| Charts     | Plotly (dark theme) |
| Refresh    | `time.sleep(25)` → `st.rerun()` |

---

# Run

```bash
pip install streamlit requests pandas plotly feedparser
streamlit run app.py
