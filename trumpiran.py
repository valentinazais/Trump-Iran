import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import feedparser
from datetime import datetime, timedelta
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
    html, body, [class*="css"] {font-family:'JetBrains Mono',monospace;background-color:#0a0a0a;color:#c0c0c0;}
    h1,h2,h3 {font-family:'JetBrains Mono',monospace !important;color:#ff2d2d !important;}
    .stMetric label {color:#888 !important;font-size:0.75rem !important;}
    .stMetric [data-testid="stMetricValue"] {color:#ff4b4b !important;font-size:1.5rem !important;}
    .stMetric [data-testid="stMetricDelta"] {color:#666 !important;}
    div[data-testid="stExpander"] {border:1px solid #222;border-radius:4px;}
    .news-item {border-left:3px solid #ff2d2d;padding:6px 12px;margin:8px 0;background:#111;}
    .status-bar {background:#111;border:1px solid #222;padding:8px 16px;border-radius:4px;margin-bottom:16px;font-size:0.8rem;color:#888;}
    .risk-high {color:#ff2d2d;font-weight:bold;font-size:1.2rem;}
    .risk-med {color:#ffa500;font-weight:bold;font-size:1.2rem;}
    .risk-low {color:#00ff88;font-weight:bold;font-size:1.2rem;}
</style>
""", unsafe_allow_html=True)

GAMMA_API = "https://gamma-api.polymarket.com/events"
CLOB_API_HISTORY = "https://clob.polymarket.com/prices-history"
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
                "prob_pct": round(prob * 100, 2),
                "volume": vol,
                "liquidity": liq,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "active": m.get("active", False),
                "token_id": token_id
            })

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values("date_obj").reset_index(drop=True)
        return df, meta

    except Exception as e:
        return pd.DataFrame(), {"error": str(e)}

@st.cache_data(ttl=300)
def fetch_history(token_ids, interval="1w"):
    history_data = []
    for t_id in token_ids:
        if not t_id:
            continue
        try:
            res = requests.get(CLOB_API_HISTORY, params={"market": t_id, "interval": interval}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for pt in data.get("history", []):
                    history_data.append({
                        "token_id": t_id,
                        "time": datetime.utcfromtimestamp(pt["t"]),
                        "price": float(pt["p"]) * 100
                    })
        except Exception:
            continue
    return pd.DataFrame(history_data)

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

def compute_hazard_rate(df):
    if df.empty or len(df) < 2:
        return df
    rates = [0]
    for i in range(1, len(df)):
        p_prev = df.iloc[i - 1]["prob"]
        p_curr = df.iloc[i]["prob"]
        delta_p = p_curr - p_prev
        survival = 1 - p_prev
        if survival > 0.001:
            h = delta_p / survival
        else:
            h = 0
        rates.append(round(h * 100, 3))
    df = df.copy()
    df["hazard_pct"] = rates
    return df


df, meta = fetch_polymarket()
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

st.markdown("# US STRIKES IRAN — PROBABILITY TERMINAL")

if meta.get("error"):
    st.error(f"API fetch error: {meta['error']}")

if not df.empty:
    max_prob = df["prob_pct"].max()
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
    m1.metric("Peak CDF Probability", f"{max_prob:.1f}%")
    m2.metric("Total Volume", f"${total_vol:,.0f}")
    m3.metric("Total Liquidity", f"${total_liq:,.0f}")
    m4.metric("Avg Bid-Ask Spread", f"{avg_spread:.4f}")
    m5.markdown(f"**Threat Level**<br><span class='{risk_class}'>{risk_label}</span>", unsafe_allow_html=True)

    st.markdown("---")

left, right = st.columns([5, 2])

with left:
    if not df.empty:
        col_title, col_sel = st.columns([4, 1])
        col_title.markdown("### Historical Probability Tracking")
        interval_choice = col_sel.selectbox("Timeframe", ["1d", "1w", "max"], index=1, label_visibility="collapsed")
        
        top_tokens = df.nlargest(4, 'prob_pct')['token_id'].tolist()
        df_hist = fetch_history(top_tokens, interval_choice)
        
        fig_hist = go.Figure()
        if not df_hist.empty:
            for t_id in top_tokens:
                contract_label = df[df['token_id'] == t_id]['label'].values[0]
                contract_data = df_hist[df_hist['token_id'] == t_id]
                fig_hist.add_trace(go.Scatter(
                    x=contract_data['time'],
                    y=contract_data['price'],
                    mode='lines',
                    name=contract_label,
                    hovertemplate="%{x}<br>Prob: %{y:.1f}%<extra></extra>"
                ))
        fig_hist.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0a0a",
            plot_bgcolor="#0a0a0a",
            yaxis=dict(title="Probability (%)", gridcolor="#1a1a1a"),
            xaxis=dict(title="", gridcolor="#1a1a1a"),
            margin=dict(l=40, r=20, t=10, b=30),
            height=320,
            font=dict(family="JetBrains Mono", size=11, color="#888"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("### Cumulative Distribution — P(Strike ≤ t)")
        fig_cdf = go.Figure()
        fig_cdf.add_trace(go.Scatter(
            x=df["label"],
            y=df["prob_pct"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#ff2d2d", width=2),
            marker=dict(size=8, color="#ff2d2d"),
            fillcolor="rgba(255,45,45,0.1)",
            name="P(Strike ≤ t)",
            hovertemplate="%{x}<br>Probability: %{y:.2f}%<extra></extra>"
        ))
        fig_cdf.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0a0a",
            plot_bgcolor="#0a0a0a",
            yaxis=dict(title="Cumulative Probability (%)", range=[0, max(100, max_prob + 15)], gridcolor="#1a1a1a"),
            xaxis=dict(title="", gridcolor="#1a1a1a", tickangle=-45),
            margin=dict(l=40, r=20, t=10, b=80),
            height=320,
            font=dict(family="JetBrains Mono", size=11, color="#888"),
        )
        st.plotly_chart(fig_cdf, use_container_width=True)

        col_vol, col_haz = st.columns(2)
        with col_vol:
            st.markdown("### Market Volume by Target Date")
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(
                x=df["label"],
                y=df["volume"],
                marker_color="#ffa500",
                hovertemplate="%{x}<br>Volume: $%{y:,.0f}<extra></extra>"
            ))
            fig_vol.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0a0a",
                plot_bgcolor="#0a0a0a",
                yaxis=dict(title="Volume ($)", gridcolor="#1a1a1a"),
                xaxis=dict(title="", gridcolor="#1a1a1a", tickangle=-45),
                margin=dict(l=30, r=10, t=10, b=60),
                height=260,
                font=dict(family="JetBrains Mono", size=11, color="#888"),
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        with col_haz:
            df_h = compute_hazard_rate(df)
            st.markdown("### Hazard Rate — h(t)")
            fig_hazard = go.Figure()
            colors = ["#ff2d2d" if v > 0 else "#00ff88" for v in df_h["hazard_pct"]]
            fig_hazard.add_trace(go.Bar(
                x=df_h["label"],
                y=df_h["hazard_pct"],
                marker_color=colors,
                hovertemplate="%{x}<br>h(t): %{y:.3f}%<extra></extra>"
            ))
            fig_hazard.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0a0a",
                plot_bgcolor="#0a0a0a",
                yaxis=dict(title="Hazard Rate (%)", gridcolor="#1a1a1a"),
                xaxis=dict(title="", gridcolor="#1a1a1a", tickangle=-45),
                margin=dict(l=30, r=10, t=10, b=60),
                height=260,
                font=dict(family="JetBrains Mono", size=11, color="#888"),
            )
            st.plotly_chart(fig_hazard, use_container_width=True)

        with st.expander("RAW MARKET DATA TABLE"):
            display_df = df[["label", "prob_pct", "volume", "liquidity", "spread"]].copy()
            display_df.columns = ["Contract", "Prob %", "Volume $", "Liquidity $", "Spread"]
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
                <a href="{item['link']}" target="_blank" style="color:#ff4b4b;text-decoration:none;font-size:0.85rem;">
                    {item['title']}
                </a>
                <br><span style="color:#555;font-size:0.7rem;">{item['published']}{source}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("News feed fetch failed.")

    st.markdown("---")
    st.markdown("### ANALYTICS INSIGHTS")
    st.markdown("""
    <div style="font-size:0.8rem;color:#999;line-height:1.6;background:#111;padding:12px;border:1px solid #222;border-radius:4px;">
    <strong style="color:#fff;">Historical Trend</strong><br>
    Identifies momentum behind specific contract execution dates. Sudden convergence across dates indicates systemic escalation rather than a specific targeted timeline.<br><br>
    <strong style="color:#fff;">Volume Allocation</strong><br>
    Capital clusters around highest-conviction dates. Contracts with extreme probability but low volume signify retail panic. High volume signifies institutional or informed positioning.<br><br>
    <strong style="color:#fff;">Hazard Identification</strong><br>
    Elevated instantaneous hazard rate isolated to a specific forward-date flags it as the primary focal point of the prediction market consensus for the kinetic event.
    </div>
    """, unsafe_allow_html=True)

time.sleep(25)
st.rerun()
