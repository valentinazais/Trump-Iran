import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import feedparser
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configure Dashboard
st.set_page_config(page_title="Terminal | US-Iran Strike Probability", layout="wide", initial_sidebar_state="collapsed")

# Inject minimal CSS
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    h1 { font-family: monospace; color: #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="data_refresh")

# Constants
GAMMA_API = "https://gamma-api.polymarket.com/events"
SLUG = "us-strikes-iran-by"
NEWS_RSS = "https://news.google.com/rss/search?q=Trump+Iran+military+strike&hl=en-US&gl=US&ceid=US:en"

@st.cache_data(ttl=30)
def fetch_market_data():
    """Extract live order book probabilities."""
    res = requests.get(f"{GAMMA_API}?slug={SLUG}")
    if res.status_code != 200:
        return pd.DataFrame()
    
    data = res.json()
    if not data:
        return pd.DataFrame()
    
    markets = data[0].get("markets", [])
    records = []
    
    for m in markets:
        if m.get("closed") or not m.get("active"):
            continue
            
        group_item_title = m.get("groupItemTitle", "")
        # Filter for dates leading up to Jun 30, prioritize Feb dates
        if not group_item_title:
            continue
            
        try:
            # Parse prices
            prices = eval(m.get("outcomePrices", "[]"))
            outcomes = eval(m.get("outcomes", "[]"))
            
            if "Yes" in outcomes:
                idx = outcomes.index("Yes")
                prob = float(prices[idx])
                
                # Attempt to parse date for sorting
                try:
                    date_obj = datetime.strptime(f"{group_item_title} 2026", "%b %d %Y")
                except ValueError:
                    date_obj = datetime.max
                    
                records.append({
                    "Date": group_item_title,
                    "Probability": prob,
                    "Sort_Date": date_obj,
                    "Volume": float(m.get("volume", 0))
                })
        except Exception:
            continue
            
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("Sort_Date").drop(columns=["Sort_Date"])
        # Format for CDF \( P(T \le t) \)
        df["CDF_Percent"] = df["Probability"] * 100
    return df

@st.cache_data(ttl=300)
def fetch_news():
    """Scrape RSS feed for geopolitical triggers."""
    feed = feedparser.parse(NEWS_RSS)
    return feed.entries[:8]

# Data Fetch
df_markets = fetch_market_data()
news_items = fetch_news()

# UI Layout
st.title("TACTICAL DASHBOARD: US STRIKES IRAN")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Cumulative Distribution Function \( P(T \le t) \)")
    if not df_markets.empty:
        # Plotly CDF Curve
        fig = px.area(
            df_markets, 
            x="Date", 
            y="CDF_Percent", 
            markers=True,
            title="Probability of Strike by Date",
            labels={"CDF_Percent": "Cumulative Probability (%)", "Date": "Target Date"},
            color_discrete_sequence=["#ff4b4b"]
        )
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Probability (%)",
            yaxis_range=[0, max(100, df_markets["CDF_Percent"].max() + 10)],
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Metrics Row
        st.subheader("Live Market Pricing")
        cols = st.columns(len(df_markets.head(4)))
        for i, row in df_markets.head(4).iterrows():
            cols[i].metric(
                label=row['Date'], 
                value=f"{row['CDF_Percent']:.1f}%",
                delta=f"Vol: ${row['Volume']:,.0f}",
                delta_color="off"
            )
    else:
        st.error("API Error: Polymarket Gamma unvailable.")

with col2:
    st.subheader("Intelligence Feed")
    st.markdown("---")
    for item in news_items:
        pub_date = item.published if hasattr(item, 'published') else "Recent"
        st.markdown(f"**[{item.title}]({item.link})**")
        st.caption(f"Time: {pub_date}")
        st.markdown("<br>", unsafe_allow_html=True)