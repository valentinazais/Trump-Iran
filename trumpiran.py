import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import feedparser
from datetime import datetime, timezone
import time
import json

st.set_page_config(
    page_title="US-Iran Strike Probability Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');
    .block-container {padding-top:1rem;padding-bottom:0rem;max-width:1400px;}
    html, body, [class*="css"] {font-family:'JetBrains Mono',monospace;background-color:#0d1117;color:#c9d1d9;font-weight:300;}
    h1,h2,h3 {font-family:'JetBrains Mono',monospace !important;color:#58a6ff !important;font-weight:500;letter-spacing:-0.5px;}
    .stMetric label {color:#8b949e !important;font-size:0.70rem !important;text-transform:uppercase;letter-spacing:0.5px;}
    .stMetric [data-testid="stMetricValue"] {color:#c9d1d9 !important;font-size:1.6rem !important;font-weight:500;}
    .stMetric [data-testid="stMetricDelta"] {color:#8b949e !important;}
    div[data-testid="stExpander"] {border:1px solid #21262d;border-radius:2px;background:#0d1117;}
    .news-item {border-left:2px solid #58a6ff;padding:4px 10px;margin:8px 0;background:transparent;border-bottom:1px solid #161b22;transition:background 0.2s;}
    .news-item:hover {background:#161b22;}
    .status-bar {background:#0d1117;border-bottom:1px solid #21262d;padding:6px 12px;margin-bottom:16px;font-size:0.75rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.5px;}
    .risk-high {color:#f85149;font-weight:700;font-size:1.1rem;letter-spacing:1px;}
    .risk-med {color:#d29922;font-weight:700;font-size:1.1rem;letter-spacing:1px;}
    .risk-low {color:#2ea043;font-weight:700;font-size:1.1rem;letter-spacing:1px;}
    .insight-box {font-size:0.8rem;color:#c9d1d9;line-height:1.5;background:#161b22;padding:10px;border:1px solid #30363d;border-radius:2px;margin-bottom:10px;}
    .insight-hl {color:#58a6ff;font-weight:500;}
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
            if m.get("closed"): continue
            title = m.get("groupItemTitle", "") or m.get("question", "")
            if not title: continue

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

            if "Yes" not in outcomes: continue

            idx = outcomes.index("Yes")
            prob = float(prices[idx])
            token_id = clob_ids[idx] if len(clob_ids) > idx else None

            date_obj = None
            for fmt in ["%b %d", "%B %d", "%b %d, %Y", "%B %d, %Y"]:
                try:
                    parsed = datetime.strptime(title.strip(), fmt)
                    if parsed.year == 1900: parsed = parsed.replace(year=2026)
                    date_obj = parsed
                    break
                except ValueError:
                    continue

            if date_obj is None:
                tl = title.lower()
                day = ''.join(filter(str.isdigit, tl))
                if not day: continue
                if "feb" in tl: date_obj = datetime(2026, 2, int(day))
                elif "mar" in tl: date_obj = datetime(2026, 3, int(day))
                elif "apr" in tl: date_obj = datetime(2026, 4, int(day))

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
        for entry in feed.entries:
            dt = datetime.utcnow()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
            
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "dt": dt,
                "source": entry.get("source", {}).get("title", ""),
            })
        
        # Sort by latest first
        items.sort(key=lambda x: x["dt"], reverse=True)
        return items[:12]
    except Exception:
        return []

def format_time_ago(dt):
    delta = datetime.utcnow().replace(tzinfo=timezone.utc) - dt
    secs = delta.total_seconds()
    if secs < 3600: return f"{int(secs // 60)}m ago"
    if secs < 86400: return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"

def compute_distributions(df):
    if df.empty: return df
    df = df.sort_values("date_obj").reset_index(drop=True)
    
    df["cdf"] = df["prob"]
    df["cdf_pct"] = df["cdf"] * 100

    pmf = [df["cdf"].iloc[0]]
    for i in range(1, len(df)):
        val = df["cdf"].iloc[i] - df["cdf"].iloc[i-1]
        pmf.append(max(0, val))
    df["pmf"] = pmf
    df["pmf_pct"] = df["pmf"] * 100

    df["survival"] = 1.0 - df["cdf"]
    df["survival_pct"] = df["survival"] * 100

    hazard = [df["pmf"].iloc[0]]
    for i in range(1, len(df)):
        surv_prev = df["survival"].iloc[i-1]
        hazard.append(df["pmf"].iloc[i] / surv_prev if surv_prev > 0.001 else 0)
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
    SYS_TIME: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC &nbsp;|&nbsp;
    EXPIRY: {DEADLINE.strftime('%Y-%m-%d')} &nbsp;|&nbsp;
    T-MINUS: {days_left}D &nbsp;|&nbsp;
    PING: 25s
</div>
""", unsafe_allow_html=True)

st.markdown("<h1>US STRIKES IRAN LIVE DASHBOARD</h1>", unsafe_allow_html=True)

if meta.get("error"):
    st.error(f"API fetch error: {meta['error']}")

if not df.empty:
    max_prob = df["cdf_pct"].max()
    total_vol = meta.get("volume", df["volume"].sum())
    total_liq = meta.get("liquidity", df["liquidity"].sum())
    avg_spread = df["spread"].mean()

    if max_prob >= 50: risk_class, risk_label = "risk-high", "HIGH"
    elif max_prob >= 20: risk_class, risk_label = "risk-med", "ELEVATED"
    else: risk_class, risk_label = "risk-low", "LOW"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("PEAK CUMULATIVE RISK", f"{max_prob:.1f}%")
    m2.metric("TOTAL VOLUME", f"${total_vol:,.0f}")
    m3.metric("TOTAL LIQUIDITY", f"${total_liq:,.0f}")
    m4.metric("AVG SPREAD", f"{avg_spread:.4f}")
    m5.markdown(f"**THREAT POSTURE**<br><span class='{risk_class}'>{risk_label}</span>", unsafe_allow_html=True)

    st.markdown("---")

left, right = st.columns([5, 2])

with left:
    if not df.empty:
        st.markdown("### PROBABILITY MASS FUNCTION [ΔP]")
        fig_pmf = go.Figure(go.Bar(
            x=df["label"], y=df["pmf_pct"],
            marker_color="#1f6feb",
            hovertemplate="%{x}<br>PMF: %{y:.2f}%<extra></extra>"
        ))
        fig_pmf.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            yaxis=dict(title="Prob (%)", gridcolor="#21262d", zerolinecolor="#30363d"),
            xaxis=dict(title="", gridcolor="#21262d", tickangle=-45),
            margin=dict(l=40, r=20, t=10, b=40), height=240,
            font=dict(family="JetBrains Mono", size=10, color="#8b949e")
        )
        st.plotly_chart(fig_pmf, use_container_width=True)

        st.markdown("### CUMULATIVE DISTRIBUTION FUNCTION [P(T ≤ t)]")
        fig_cdf = go.Figure(go.Scatter(
            x=df["label"], y=df["cdf_pct"], mode="lines+markers",
            line=dict(color="#58a6ff", width=1.5), marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.05)",
            hovertemplate="%{x}<br>CDF: %{y:.2f}%<extra></extra>"
        ))
        fig_cdf.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            yaxis=dict(title="Prob (%)", gridcolor="#21262d", range=[0, max(100, max_prob + 10)], zerolinecolor="#30363d"),
            xaxis=dict(title="", gridcolor="#21262d", tickangle=-45),
            margin=dict(l=40, r=20, t=10, b=40), height=240,
            font=dict(family="JetBrains Mono", size=10, color="#8b949e")
        )
        st.plotly_chart(fig_cdf, use_container_width=True)

        col_surv, col_haz = st.columns(2)
        with col_surv:
            st.markdown("### SURVIVAL FUNCTION [1 - CDF]")
            fig_surv = go.Figure(go.Scatter(
                x=df["label"], y=df["survival_pct"], mode="lines+markers",
                line=dict(color="#8b949e", width=1.5), marker=dict(size=5),
                hovertemplate="%{x}<br>Survival: %{y:.2f}%<extra></extra>"
            ))
            fig_surv.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                yaxis=dict(title="Prob (%)", gridcolor="#21262d", range=[0, 105], zerolinecolor="#30363d"),
                xaxis=dict(title="", gridcolor="#21262d", tickangle=-45),
                margin=dict(l=40, r=20, t=10, b=40), height=220,
                font=dict(family="JetBrains Mono", size=10, color="#8b949e")
            )
            st.plotly_chart(fig_surv, use_container_width=True)

        with col_haz:
            st.markdown("### HAZARD RATE [h(t)]")
            fig_haz = go.Figure(go.Bar(
                x=df["label"], y=df["hazard_pct"],
                marker_color="#d29922",
                hovertemplate="%{x}<br>Hazard: %{y:.2f}%<extra></extra>"
            ))
            fig_haz.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                yaxis=dict(title="Rate (%)", gridcolor="#21262d", zerolinecolor="#30363d"),
                xaxis=dict(title="", gridcolor="#21262d", tickangle=-45),
                margin=dict(l=40, r=20, t=10, b=40), height=220,
                font=dict(family="JetBrains Mono", size=10, color="#8b949e")
            )
            st.plotly_chart(fig_haz, use_container_width=True)

        with st.expander("RAW MARKET DATA MATRIX"):
            display_df = df[["label", "cdf_pct", "pmf_pct", "survival_pct", "hazard_pct", "volume", "spread"]].copy()
            display_df.columns = ["Target Date", "CDF (%)", "PMF (%)", "Survival (%)", "Hazard (%)", "Volume ($)", "Spread"]
            st.dataframe(display_df.round(3), use_container_width=True, hide_index=True)

with right:
    
    st.markdown("### Live news")
    if news:
        for item in news:
            source = f" — {item['source']}" if item['source'] else ""
            time_str = format_time_ago(item['dt'])
            st.markdown(f"""
            <div class="news-item">
                <a href="{item['link']}" target="_blank" style="color:#c9d1d9;text-decoration:none;font-size:0.8rem;font-weight:400;letter-spacing:-0.2px;">
                    {item['title']}
                </a>
                <br><span style="color:#8b949e;font-size:0.65rem;text-transform:uppercase;">[{time_str}]{source}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#8b949e;font-size:0.8rem;'>NO SIGNAL DETECTED.</div>", unsafe_allow_html=True)
    # Volume Intelligence
    if not df.empty:
        st.markdown("### Volume data")
        max_vol_row = df.loc[df['volume'].idxmax()]
        max_pmf_row = df.loc[df['pmf_pct'].idxmax()]
        vol_concentration = (max_vol_row['volume'] / df['volume'].sum() * 100) if df['volume'].sum() > 0 else 0
        
        st.markdown(f"""
        <div class="insight-box">
            Capital Concentration: <span class="insight-hl">{vol_concentration:.1f}%</span> deployed on <strong>{max_vol_row['label']}</strong> (${max_vol_row['volume']:,.0f}).<br><br>
            Highest Marginal Risk: <strong>{max_pmf_row['label']}</strong> holds the highest isolated kinetic probability (<span class="insight-hl">+{max_pmf_row['pmf_pct']:.1f}%</span>).<br><br>
            Spread Velocity: Tighter spreads indicate high institutional conviction. Current average is <span class="insight-hl">{avg_spread:.4f}</span>.
        </div>
        """, unsafe_allow_html=True)
    
time.sleep(25)
st.rerun()
