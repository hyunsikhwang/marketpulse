import streamlit as st
import yfinance as yf
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Global Index Tracker (ECharts)",
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

st.title("🌍 Global Stock Index Performance (ECharts)")
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
    today = datetime.now()
    current_year = today.year
    start_date = datetime(current_year - 1, 12, 15).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    all_data = pd.DataFrame()
    for name, ticker in indices_dict.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date)['Close']
            if not data.empty:
                if isinstance(data, pd.DataFrame):
                    data = data.iloc[:, 0]
                all_data[name] = data
        except Exception as e:
            st.error(f"Error fetching {name}: {e}")
    return all_data

with st.spinner('데이터를 불러오고 있습니다...'):
    df = fetch_data(indices)

if not df.empty:
    current_year = datetime.now().year
    prev_year_data = df[df.index.year == (current_year - 1)]
    
    if not prev_year_data.empty:
        last_close_prev_year = prev_year_data.iloc[-1]
        current_year_df = df[df.index.year == current_year]
        combined_df = pd.concat([prev_year_data.tail(1), current_year_df])
        normalized_df = (combined_df / last_close_prev_year) * 100
        
        # Metrics Display
        cols = st.columns(4)
        for i, (name, val) in enumerate(normalized_df.iloc[-1].items()):
            col = cols[i % 4]
            ytd_pct = val - 100
            col.metric(name, f"{val:.2f}", f"{ytd_pct:+.2f}%")

        # ECharts Visualization
        x_data = normalized_df.index.strftime('%Y-%m-%d').tolist()
        
        line = (
            Line(init_opts=opts.InitOpts(theme="dark", height="600px", width="100%"))
            .add_xaxis(xaxis_data=x_data)
        )
        
        for name in normalized_df.columns:
            line.add_yaxis(
                series_name=name,
                y_axis=normalized_df[name].round(2).tolist(),
                symbol="none",
                is_smooth=True,
                label_opts=opts.LabelOpts(is_show=False),
            )
            
        line.set_global_opts(
            title_opts=opts.TitleOpts(title="Index Performance (Base 100)", subtitle="Relative to Prev Year Close"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            legend_opts=opts.LegendOpts(pos_top="5%", pos_right="5%"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(
                type_="value", 
                min_="dataMin",
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
            datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider")],
        )
        
        # Add MarkLine for 100 baseline
        line.set_series_opts(
            markline_opts=opts.MarkLineOpts(
                data=[opts.MarkLineItem(y=100, name="Prev Year Close")],
                linestyle_opts=opts.LineStyleOpts(type_="dashed", color="gray", opacity=0.5)
            )
        )

        st_pyecharts(line, height="650px", key="index_chart")
        
        with st.expander("Raw Data (Normalized)"):
            st.dataframe(normalized_df.style.format("{:.2f}"))
    else:
        st.warning(f"전년도({current_year - 1}) 데이터를 찾을 수 없습니다.")
else:
    st.error("데이터를 불러오지 못했습니다.")

st.sidebar.info("""
### Information
- **Source**: Yahoo Finance
- **Charts**: ECharts (pyecharts)
- **Indices**: S&P500, NASDAQ, Dow Jones, Nikkei 225, Nifty50, Sensex, KOSPI, KOSDAQ
""")
