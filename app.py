import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Global Index Tracker",
    page_icon="📈",
    layout="wide"
)

# Custom CSS for premium look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌍 Global Stock Index Performance")
st.markdown("전년도 마지막 종가 기준 올해 수익률 추이 (Base 100)")

# Indices definition
indices = {
    'S&P500': '^GSPC',
    'NASDAQ': '^IXIC',
    'Dow Jones Industry': '^DJI',
    'Nikkei 225': '^N225',
    'Nifty50': '^NSEI',
    'Sensex': '^BSESN',
    'KOSPI': '^KS11',
    'KOSDAQ': '^KQ11'
}

@st.cache_data(ttl=3600)
def fetch_data(indices_dict):
    # Current date
    today = datetime.now()
    current_year = today.year
    
    # Start date to ensure we get the last trading day of the previous year
    # Taking Dec 15th of previous year to stay safe
    start_date = datetime(current_year - 1, 12, 15).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    all_data = pd.DataFrame()
    
    for name, ticker in indices_dict.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date)['Close']
            if not data.empty:
                # Flatten MultiIndex if necessary (yfinance v0.2.40+ might return MultiIndex)
                if isinstance(data, pd.DataFrame):
                    data = data.iloc[:, 0]
                all_data[name] = data
        except Exception as e:
            st.error(f"Error fetching {name}: {e}")
            
    return all_data

with st.spinner('데이터를 불러오고 있습니다...'):
    df = fetch_data(indices)

if not df.empty:
    # 1. Identify the last trading day of the previous year
    current_year = datetime.now().year
    prev_year_data = df[df.index.year == (current_year - 1)]
    
    if not prev_year_data.empty:
        last_close_prev_year = prev_year_data.iloc[-1]
        
        # 2. Filter data for the current year
        current_year_df = df[df.index.year == current_year]
        
        # 3. Add the last close of previous year as the starting point (index 0) 
        # for visualization to show growth from Day 1.
        combined_df = pd.concat([prev_year_data.tail(1), current_year_df])
        
        # 4. Normalize to Base 100
        normalized_df = (combined_df / last_close_prev_year) * 100
        
        # Metrics Display
        cols = st.columns(4)
        for i, (name, val) in enumerate(normalized_df.iloc[-1].items()):
            col = cols[i % 4]
            ytd_pct = val - 100
            col.metric(name, f"{val:.2f}", f"{ytd_pct:+.2f}%")

        # Visualization
        fig = go.Figure()

        for column in normalized_df.columns:
            fig.add_trace(go.Scatter(
                x=normalized_df.index,
                y=normalized_df[column],
                mode='lines',
                name=column,
                hovertemplate='%{x}<br>' + f'{column}: ' + '%{y:.2f}' + '<extra></extra>'
            ))

        fig.update_layout(
            template='plotly_dark',
            xaxis_title="Date",
            yaxis_title="Base 100 (Indexed to Prev Year Close)",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            height=600
        )
        
        # Highlight the 100 baseline
        fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Prev Year Close")

        st.plotly_chart(fig, use_container_width=True)
        
        # Raw Data Section
        with st.expander("Raw Data (Normalized)"):
            st.dataframe(normalized_df.style.format("{:.2f}"))
    else:
        st.warning(f"전년도({current_year - 1}) 데이터를 찾을 수 없습니다. 현재 날짜: {datetime.now().strftime('%Y-%m-%d')}")
        st.subheader("실제 가격 데이터")
        st.dataframe(df)
else:
    st.error("데이터를 불러오지 못했습니다. Ticker 심볼을 확인하거나 네트워크 상태를 점검해주세요.")

st.sidebar.info("""
### Information
- **Source**: Yahoo Finance
- **Method**: 전년도 마지막 종가(Close)를 100으로 설정하여 현재까지의 수익률을 계산합니다.
- **Indices**: S&P500, NASDAQ, Dow Jones, Nikkei 225, Nifty50, Sensex, KOSPI, KOSDAQ
""")
