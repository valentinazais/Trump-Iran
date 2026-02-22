# US–Iran Strike Probability Dashboard

Real-time Streamlit dashboard tracking the market-implied probability of US military strikes on Iran using Polymarket event data.  
Constructs a discrete time distribution: PMF, CDF, Survival, and Hazard.

All formulas use Unicode mathematical notation to ensure proper GitHub README rendering.

---

# Distribution Construction

Let:

- tᵢ = ordered target dates  
- F(tᵢ) = cumulative probability (CDF)  
- pᵢ = probability mass (PMF)  
- S(tᵢ) = survival probability  
- h(tᵢ) = hazard rate  

---

## 1. Cumulative Distribution Function (CDF)

Definition:

F(tᵢ) = Yes market price at tᵢ  

Percentage form:

F%(tᵢ) = 100 × F(tᵢ)

Interpretation: probability the event has occurred on or before date tᵢ.

---

## 2. Probability Mass Function (PMF)

First node:

p₁ = F(t₁)

Recursive difference:

pᵢ = max(0, F(tᵢ) − F(tᵢ₋₁))

Percentage form:

p%(tᵢ) = 100 × pᵢ

Interpretation: marginal probability assigned specifically to bucket tᵢ.

---

## 3. Survival Function

Definition:

S(tᵢ) = 1 − F(tᵢ)

Percentage form:

S%(tᵢ) = 100 × S(tᵢ)

Interpretation: probability the event has not occurred by date tᵢ.

---

## 4. Hazard Rate

First node:

h(t₁) = p₁

Recursive definition:

h(tᵢ) = pᵢ / S(tᵢ₋₁)   if S(tᵢ₋₁) > 0.001  
h(tᵢ) = 0              otherwise  

Percentage form:

h%(tᵢ) = 100 × h(tᵢ)

Interpretation: conditional probability of occurrence at tᵢ given survival until tᵢ₋₁.

---

# Dashboard Components

## Top Metrics

- Peak cumulative risk (max F)
- Total volume
- Total liquidity
- Average bid–ask spread

Risk classification:

| Max F | Label     |
|--------|-----------|
| ≥ 50%  | HIGH      |
| ≥ 20%  | ELEVATED  |
| < 20%  | LOW       |

---

## Main Charts

- PMF — marginal probability per date (bar chart)
- CDF — cumulative probability (line + area)
- Survival — remaining probability (line)
- Hazard — conditional event intensity (bar chart)

---

## Raw Market Table

| Column        | Description |
|---------------|------------|
| Target Date   | Event bucket date |
| CDF (%)       | F%(tᵢ) |
| PMF (%)       | p%(tᵢ) |
| Survival (%)  | S%(tᵢ) |
| Hazard (%)    | h%(tᵢ) |
| Volume ($)    | Capital deployed |
| Spread        | Bid–ask spread |

---

# Volume Intelligence

Let:

- Vᵢ = volume at node i  
- Vₜₒₜ = Σ Vᵢ  

Capital concentration:

Concentration = (max(Vᵢ) / Vₜₒₜ) × 100

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
| Refresh    | time.sleep(25) → st.rerun() |

---

# Run

```bash
pip install streamlit requests pandas plotly feedparser
streamlit run app.py
