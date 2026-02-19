import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import feedparser
from datetime import datetime
import time
import json

st.set_page_config(
    page_title="US-Iran Strike Probability Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    .block-container {padding-top:1rem;padding-bottom:0rem;max-width:1400px;}
    html, body, [class*="css"] {font-family:'JetBrains Mono',monospace;background-color:#0d1117;color:#c9d1d9;}
    h1,h2,h3 {font-family:'JetBrains Mono',monospace !important;color:#58a6ff !important;}
    .stMetric label {color:#8b949e !important;font-size:0.75rem !important;}
    .stMetric [data-testid="stMetricValue"] {color:#c9d1d9 !important;font-size:1.5rem !important;}
    .stMetric [data-testid="stMetricDelta"] {color:#8b949e !important;}
    div[data-testid="stExpander"] {border:1px solid #30363d;border-radius:4px;}
    .news-item {border-left:3px solid #58a6ff;padding:6px 12px;margin:8px 0;background:#161b22;}
    .status-bar {background:#161b22;border:1px solid #30363d;padding:8px 16px;border-radius:4px;margin-bottom:16px;font-size:0.8rem;color:#8b949e;}
    .risk-high {color:#f85149;font-weight:bold;font-size:1.2rem;}
    .risk-med {color:#d29922;font-weight:bold;font-size:1.2rem;}
    .risk-low {color:#2ea043;font-weight:bold;font-size:1.2rem;}
</style>
""", unsafe_allow_html=True)

GAMMA_API = "https://gamma-api.polymarket.com/events"
NEWS_RSS = "https://news.google.com/rss/search?q=Trump+Iran+military+strike&hl=en-US&gl=US&ceid=US:en"
DEADLINE = datetime(2026, 6, 30, 23, 59, 59)

@st.cache_data(ttl=25)
def fetch_polymarket():
    try:
        res = requests.get(GAMMA_API, params={"slug": "us-strikes-iran-by"}, timeout=10)
        if res.status_code != 200:
            return pd.DataFrame(), {}
        data = res.json()
        if not data:
            return pd.DataFrame(), {}

        event = data[0]
        meta = {
            "title": event.get("title", ""),
            "liquidity": float(event.get("liquidity", 0)),
            "volume": float(event.get("volume", 0)),
            "startDate": event.get("startDate", ""),
        }

        markets = event.get("markets", [])
        records = []

        for m in markets:
            if m.get("closed"):
                continue

            title = m.get("groupItemTitle", "") or m.get("question", "")
            if not title:
                continue

            try:
                outcomes = json.loads(m.get("outcomes", "[]"))
                prices = json.loads(m.get("outcomePrices", "[]"))
                clob_ids = json.loads(m.get("clobTokenIds", "[]"))
            except (json.JSONDecodeError, TypeError):
                try:
                    outcomes = eval(m.get("outcomes", "[]"))
                    prices = eval(m.get("outcomePrices", "[]"))
                    clob_ids = eval(m.get("clobTokenIds", "[]"))
                except Exception:
                    continue

            if "Yes" not in outcomes:
                continue

            idx = outcomes.index("Yes")
            prob = float(prices[idx])
            token_id = clob_ids[idx] if len(clob_ids) > idx else None

            date_obj = None
            for fmt in ["%b %d", "%B %d", "%b %d, %Y", "%B %d, %Y"]:
                try:
                    parsed = datetime.strptime(title.strip(), fmt)
                    if parsed.year == 1900:
                        parsed = parsed.replace(year=2026)
                    date_obj = parsed
                    break
                except ValueError:
                    continue

            if date_obj is None:
                if "feb" in title.lower():
                    day = ''.join(filter(str.isdigit, title))
                    if day: date_obj = datetime(2026, 2, int(day))
                elif "mar" in title.lower():
                    day = ''.join(filter(str.isdigit, title))
                    if day: date_obj = datetime(2026, 3, int(day))
                elif "apr" in title.lower():
                    day = ''.join(filter(str.isdigit, title))
                    if day: date_obj = datetime(2026, 4, int(day))

            vol = float(m.get("volume", 0))
            liq = float(m.get("liquidity", 0))
            best_bid = float(m.get("bestBid", 0))
            best_ask = float(m.get("bestAsk", 0))
            spread = best_ask - best_bid if best_ask and best_bid else 0

            records.append({
                "label": title,
                "date_obj": date_obj if date_obj else datetime(2099, 1, 1),
                "prob": prob,
                "volume": vol,
                "liquidity": liq,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "token_id": token_id
            })

        df = pd.DataFrame(records)
        return df, meta

    except Exception as e:
        return pd.DataFrame(), {"error": str(e)}

@st.cache_data(ttl=120)
def fetch_news():
    try:
        feed = feedparser.parse(NEWS_RSS)
        items = []
        for entry in feed.entries[:10]:
            pub = entry.get("published", "")
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": pub,
                "source": entry.get("source", {}).get("title", ""),
            })
        return items
    except Exception:
        return []

def compute_distributions(df):
    if df.empty: return df
    df = df.sort_values("date_obj").reset_index(drop=True)
    
    # CDF (Cumulative Distribution Function)
    df["cdf"] = df["prob"]
    df["cdf_pct"] = df["cdf"] * 100

    # PMF (Probability Mass Function / Discrete PDF)
    pmf = [df["cdf"].iloc[0]]
    for i in range(1, len(df)):
        val = df["cdf"].iloc[i] - df["cdf"].iloc[i-1]
        pmf.append(max(0, val))
    df["pmf"] = pmf
    df["pmf_pct"] = df["pmf"] * 100

    # Survival Function (Inverse CDF conceptually for time-to-event)
    df["survival"] = 1.0 - df["cdf"]
    df["survival_pct"] = df["survival"] * 100

    # Hazard Rate
    hazard = [df["pmf"].iloc[0]]
    for i in range(1, len(df)):
        surv_prev = df["survival"].iloc[i-1]
        if surv_prev > 0.001:
            hazard.append(df["pmf"].iloc[i] / surv_prev)
        else:
            hazard.append(0)
    df["hazard"] = hazard
    df["hazard_pct"] = df["hazard"] * 100

    return df

df_raw, meta = fetch_polymarket()
df = compute_distributions(df_raw)
news = fetch_news()

now = datetime.utcnow()
days_left = (DEADLINE - now).days

st.markdown(f"""
<div class="status-bar">
    SYSTEM TIME (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
    MARKET DEADLINE: {DEADLINE.strftime('%Y-%m-%d')} &nbsp;|&nbsp;
    T-MINUS: {days_left} DAYS &nbsp;|&nbsp;
    DATA REFRESH: 25s
</div>
""", unsafe_allow_html=True)

st.markdown("# US STRIKES IRAN — KINETIC RISK TERMINAL")

if meta.get("error"):
    st.error(f"API fetch error: {meta['error']}")

if not df.empty:
    max_prob = df["cdf_pct"].max()
    total_vol = meta.get("volume", df["volume"].sum())
    total_liq = meta.get("liquidity", df["liquidity"].sum())
    avg_spread = df["spread"].mean()

    if max_prob >= 50:
        risk_class, risk_label = "risk-high", "HIGH"
    elif max_prob >= 20:
        risk_class, risk_label = "risk-med", "ELEVATED"
    else:
        risk_class, risk_label = "risk-low", "LOW"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Peak Cumulative Risk", f"{max_prob:.1f}%")
    m2.metric("Total Volume", f"${total_vol:,.0f}")
    m3.metric("Total Liquidity", f"${total_liq:,.0f}")
    m4.metric("Avg Bid-Ask Spread", f"{avg_spread:.4f}")
    m5.markdown(f"**Threat Level**<br><span class='{risk_class}'>{risk_label}</span>", unsafe_allow_html=True)

    st.markdown("---")

left, right = st.columns([5, 2])

with left:
    if not df.empty:
        # PMF Plot
        st.markdown("### Probability Mass Function — Discrete Density")
        fig_pmf = go.Figure()
        fig_pmf.add_trace(go.Bar(
            x=df["label"], y=df["pmf_pct"],
            marker_color="#1f6feb",
            hovertemplate="%{x}<br>PMF: %{y:.2f}%<extra></extra>"
        ))
        fig_pmf.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            yaxis=dict(title="Probability (%)", gridcolor="#30363d"),
            xaxis=dict(title="", gridcolor="#30363d", tickangle=-45),
            margin=dict(l=40, r=20, t=10, b=40), height=260,
            font=dict(family="JetBrains Mono", size=11, color="#8b949e")
        )
        st.plotly_chart(fig_pmf, use_container_width=True)

        # CDF Plot
        st.markdown("### Cumulative Distribution Function")
        fig_cdf = go.Figure()
        fig_cdf.add_trace(go.Scatter(
            x=df["label"], y=df["cdf_pct"], mode="lines+markers",
            line=dict(color="#58a6ff", width=2), marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.1)",
            hovertemplate="%{x}<br>CDF: %{y:.2f}%<extra></extra>"
        ))
        fig_cdf.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            yaxis=dict(title="Probability (%)", gridcolor="#30363d", range=[0, max(100, max_prob + 10)]),
            xaxis=dict(title="", gridcolor="#30363d", tickangle=-45),
            margin=dict(l=40, r=20, t=10, b=40), height=260,
            font=dict(family="JetBrains Mono", size=11, color="#8b949e")
        )
        st.plotly_chart(fig_cdf, use_container_width=True)

        col_surv, col_haz = st.columns(2)
        with col_surv:
            # Survival Function (Inverse CDF conceptually for time tracking)
            st.markdown("### Survival Function")
            fig_surv = go.Figure()
            fig_surv.add_trace(go.Scatter(
                x=df["label"], y=df["survival_pct"], mode="lines+markers",
                line=dict(color="#8b949e", width=2), marker=dict(size=6),
                hovertemplate="%{x}<br>Survival: %{y:.2f}%<extra></extra>"
            ))
            fig_surv.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                yaxis=dict(title="Probability (%)", gridcolor="#30363d", range=[0, 105]),
                xaxis=dict(title="", gridcolor="#30363d", tickangle=-45),
                margin=dict(l=40, r=20, t=10, b=40), height=240,
                font=dict(family="JetBrains Mono", size=11, color="#8b949e")
            )
            st.plotly_chart(fig_surv, use_container_width=True)

        with col_haz:
            # Hazard Rate
            st.markdown("### Hazard Rate")
            fig_haz = go.Figure()
            fig_haz.add_trace(go.Bar(
                x=df["label"], y=df["hazard_pct"],
                marker_color="#d29922",
                hovertemplate="%{x}<br>Hazard: %{y:.2f}%<extra></extra>"
            ))
            fig_haz.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                yaxis=dict(title="Rate (%)", gridcolor="#30363d"),
                xaxis=dict(title="", gridcolor="#30363d", tickangle=-45),
                margin=dict(l=40, r=20, t=10, b=40), height=240,
                font=dict(family="JetBrains Mono", size=11, color="#8b949e")
            )
            st.plotly_chart(fig_haz, use_container_width=True)

        with st.expander("RAW MARKET DATA & METRICS TABLE"):
            display_df = df[["label", "cdf_pct", "pmf_pct", "survival_pct", "hazard_pct", "volume", "spread"]].copy()
            display_df.columns = ["Target Date", "CDF (%)", "PMF (%)", "Survival (%)", "Hazard (%)", "Volume ($)", "Spread"]
            display_df = display_df.round(3)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("No market data returned from Polymarket API.")

with right:
    st.markdown("### LIVE RSS INTELLIGENCE")
    st.markdown("---")
    if news:
        for item in news:
            source = f" — {item['source']}" if item['source'] else ""
            st.markdown(f"""
            <div class="news-item">
                <a href="{item['link']}" target="_blank" style="color:#58a6ff;text-decoration:none;font-size:0.85rem;">
                    {item['title']}
                </a>
                <br><span style="color:#8b949e;font-size:0.7rem;">{item['published']}{source}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("News feed fetch failed.")

    st.markdown("---")
    st.markdown("### MATHEMATICAL INDICATORS")
    st.markdown("""
    <div style="font-size:0.8rem;color:#c9d1d9;line-height:1.6;background:#161b22;padding:12px;border:1px solid #30363d;border-radius:4px;">
    <strong>Cumulative Distribution Function (CDF)</strong><br>
    Represents the total market probability of a strike occurring on or before date \( t \). Direct extraction from cumulative contract pricing.<br>
    \( F(t) = P(T \le t) \)<br><br>

    <strong>Probability Mass Function (PMF)</strong><br>
    Isolates the probability of the strike occurring strictly within the interval between \( t_{i-1} \) and \( t_i \). Calculated via sequential price deltas.<br>
    \( f(t_i) = F(t_i) - F(t_{i-1}) \)<br><br>

    <strong>Survival Function</strong><br>
    Calculates the probability that no strike has occurred by date \( t \). Serves as the inverse conceptual metric to CDF.<br>
    \( S(t) = 1 - F(t) \)<br><br>

    <strong>Hazard Rate</strong><br>
    Defines the conditional probability of a strike occurring exactly at time \( t_i \), given that no strike has occurred prior to \( t_i \). Essential for identifying acute risk spikes independent of cumulative buildup.<br>
    \( h(t_i) = \frac{f(t_i)}{S(t_{i-1})} \)
    </div>
    """, unsafe_allow_html=True)

time.sleep(25)
st.rerun()
