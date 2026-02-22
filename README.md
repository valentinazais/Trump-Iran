US–Iran Strike Probability Dashboard

Real-time Streamlit dashboard tracking market-implied probability of US military strikes on Iran using Polymarket event data. Computes discrete time distribution (PMF, CDF, Survival, Hazard) and overlays live news.

Overview
- Data: Polymarket Gamma API (event slug: us-strikes-iran-by).
- Auto refresh: 25 seconds.
- Deadline: 2026-06-30 23:59:59 UTC.
- News: Google News RSS (keyword-based query).
- Output: Probability term structure + liquidity diagnostics.

Distribution Construction

Let:
- t_i = ordered target dates  
- F(t_i) = cumulative probability (CDF)  
- p_i = probability mass (PMF)  
- S(t_i) = survival probability  
- h(t_i) = hazard rate  

1) CDF  
F(t_i) = market “Yes” price  
F_pct(t_i) = 100 * F(t_i)

2) PMF (discrete difference)  
p_1 = F(t_1)  
p_i = max(0, F(t_i) - F(t_{i-1}))  
p_pct(t_i) = 100 * p_i  

3) Survival  
S(t_i) = 1 - F(t_i)  
S_pct(t_i) = 100 * S(t_i)

4) Hazard  
h(t_1) = p_1  
h(t_i) = p_i / S(t_{i-1})   if S(t_{i-1}) > 0.001  
h(t_i) = 0                  otherwise  
h_pct(t_i) = 100 * h(t_i)

Dashboard Components

Top Metrics
- Peak cumulative risk (max CDF)
- Total volume
- Total liquidity
- Average bid-ask spread

Main Charts
- PMF: marginal probability by date (bar)
- CDF: cumulative probability (line + area)
- Survival: 1 − CDF (line)
- Hazard: conditional probability (bar)

Raw Market Table
Columns:
- Target Date
- CDF (%)
- PMF (%)
- Survival (%)
- Hazard (%)
- Volume ($)
- Spread

Volume Intelligence
Let V_i be volume at date i and V_tot = sum V_i.

Capital concentration:
Concentration = max(V_i) / V_tot * 100

Identifies:
- Date with highest capital deployment
- Date with highest marginal probability (PMF)
- Average spread (liquidity proxy)

Architecture
- Data: Polymarket API (JSON)
- Parsing: outcome extraction + date normalization
- Math: discrete first differences + conditional ratios
- UI: Streamlit
- Charts: Plotly (dark theme)
- Refresh loop: time.sleep(25) + st.rerun()

Run
pip install streamlit requests pandas plotly feedparser
streamlit run app.py

Limitations
- Assumes monotonic cumulative probabilities.
- Discrete buckets only (no interpolation).
- Hazard unstable if survival approaches zero.
- News feed is keyword-based, not semantic filtered.
- Dependent on Polymarket API structure stability.
