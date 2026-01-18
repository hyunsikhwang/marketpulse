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
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dcdfe4;
        color: #31333F;
    }
    .stMetric label {
        color: #555e6d !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #1b1d21 !important;
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
    'KOSDAQ': '^KQ11',
    'CSI 300': '000300.SS',
    'SSE STAR 50': '000688.SS'
}

@st.cache_data(ttl=3600)
def fetch_data(indices_dict):
    today = datetime.now()
    current_year = today.year
    start_date = datetime(current_year - 1, 12, 10).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    tickers = list(indices_dict.values())
    names = list(indices_dict.keys())
    
    try:
        # Download all tickers at once for better indexing alignment
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            return pd.DataFrame()
            
        # Extract 'Close' prices
        if 'Close' in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else False:
            all_close = data['Close']
        else:
            # Fallback for single ticker or different structure
            all_close = data[['Close']] if 'Close' in data.columns else data
            
        # Rename columns from Ticker to Name
        # Create a mapping from Ticker to Name
        inv_indices = {v: k for k, v in indices_dict.items()}
        all_close = all_close.rename(columns=inv_indices)
        
        # Forward fill to handle different market holidays
        all_close = all_close.ffill()
        
        return all_close
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

with st.spinner('데이터를 불러오고 있습니다...'):
    df = fetch_data(indices)

if not df.empty:
    current_year = datetime.now().year
    # 1. Split data
    prev_year_df = df[df.index.year == (current_year - 1)]
    current_year_df = df[df.index.year == current_year]
    
    if not prev_year_df.empty:
        # 2. Calculate baseline for EACH index individually (last non-NaN value of prev year)
        # Since we already did ffill(), we can just take the last row of prev_year_df
        last_close_prev_year = prev_year_df.iloc[-1]
        
        # 3. Combine for visualization (including the last day of prev year)
        combined_df = pd.concat([prev_year_df.tail(1), current_year_df])
        
        # 4. Normalize to Base 100
        normalized_df = (combined_df / last_close_prev_year) * 100
        
        # Drop columns that are all NaN (if any failed to download)
        normalized_df = normalized_df.dropna(axis=1, how='all')
        
        # Custom Card Animation Layout
        import json
        original_order = list(normalized_df.columns)
        latest_perf_series = normalized_df.iloc[-1]
        sorted_order = latest_perf_series.sort_values(ascending=False).index.tolist()
        
        # 2. Generate HTML for cards
        cards_html = ""
        for name in original_order:
            val = latest_perf_series[name]
            ytd_pct = val - 100
            trend_color = "#e63946" if ytd_pct < 0 else "#2a9d8f"
            trend_symbol = "▼" if ytd_pct < 0 else "▲"
            
            # Sanitize ID: only alphanumeric
            safe_id = "".join(filter(str.isalnum, name))
            
            cards_html += f"""
            <div class="metric-card" id="card-{safe_id}" data-name="{name}">
                <div class="metric-label">{name}</div>
                <div class="metric-value">{val:.2f}</div>
                <div class="metric-trend" style="color: {trend_color};">
                    {trend_symbol} {abs(ytd_pct):.2f}%
                </div>
            </div>
            """

        # 3. Inject CSS and HTML
        st.markdown(f"""
            <style>
            .metrics-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                padding: 10px 0;
                min-height: 150px;
                position: relative;
            }}
            .metric-card {{
                background-color: #f0f2f6;
                border: 1px solid #dcdfe4;
                border-radius: 12px;
                padding: 20px;
                min-width: 200px;
                flex: 1 1 calc(25% - 15px);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                justify-content: center;
                position: relative;
                z-index: 1;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 15px rgba(0,0,0,0.15);
                z-index: 10;
            }}
            .metric-label {{ font-size: 0.9rem; color: #555e6d; font-weight: 600; margin-bottom: 8px; }}
            .metric-value {{ font-size: 1.8rem; font-weight: 800; color: #1b1d21; margin-bottom: 4px; }}
            .metric-trend {{ font-size: 1rem; font-weight: 700; }}
            
            /* Responsive */
            @media (max-width: 1200px) {{ .metric-card {{ flex: 1 1 calc(33.33% - 15px); }} }}
            @media (max-width: 768px) {{ .metric-card {{ flex: 1 1 calc(50% - 15px); }} }}
            @media (max-width: 480px) {{ .metric-card {{ flex: 1 1 100%; }} }}
            </style>
            
            <div class="metrics-container" id="metrics-grid">
                {cards_html}
            </div>
            
            <script>
            (function() {{
                const grid = document.getElementById('metrics-grid');
                if (!grid) return;
                
                const cards = Array.from(grid.querySelectorAll('.metric-card'));
                const sortedOrder = {json.dumps(sorted_order)};
                
                // 1. Capture "First" positions
                const firstRects = new Map();
                cards.forEach(card => {{
                    firstRects.set(card.getAttribute('data-name'), card.getBoundingClientRect());
                }});
                
                setTimeout(() => {{
                    // 2. Re-order in DOM to get "Last" positions
                    const sortedCards = sortedOrder.map(name => 
                        cards.find(c => c.getAttribute('data-name') === name)
                    ).filter(Boolean);
                    
                    // Detach and re-attach in order
                    sortedCards.forEach(card => grid.appendChild(card));
                    
                    // 3. Invert and Play
                    sortedCards.forEach(card => {{
                        const name = card.getAttribute('data-name');
                        const firstRect = firstRects.get(name);
                        const lastRect = card.getBoundingClientRect();
                        
                        const dx = firstRect.left - lastRect.left;
                        const dy = firstRect.top - lastRect.top;
                        
                        if (dx === 0 && dy === 0) return;
                        
                        card.style.transition = 'none';
                        card.style.transform = `translate(${{dx}}px, ${{dy}}px)`;
                        
                        // Reflow
                        card.offsetHeight;
                        
                        card.style.transition = 'transform 1s cubic-bezier(0.34, 1.56, 0.64, 1)';
                        card.style.transform = 'translate(0, 0)';
                    }});
                }}, 500);
            }})();
            </script>
        """, unsafe_allow_html=True)

        # ECharts Visualization
        st.markdown("<br>", unsafe_allow_html=True)
        x_data = normalized_df.index.strftime('%Y-%m-%d').tolist()
        
        line = (
            Line(init_opts=opts.InitOpts(theme="dark", height="600px", width="100%"))
            .add_xaxis(xaxis_data=x_data)
        )
        
        # 10 High Contrast Modern Colors
        colors = [
            '#5470c6', '#91cc75', '#fac858', '#ee6666', 
            '#73c0de', '#3ba272', '#fc8452', '#9a60b4',
            '#ea7ccc', '#516b91'
        ]
        
        for i, name in enumerate(normalized_df.columns):
            line.add_yaxis(
                series_name=name,
                y_axis=normalized_df[name].round(2).tolist(),
                symbol="none",
                is_smooth=False,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2),
                # Show label at the end of the line for easy identification
                end_label_opts=opts.LabelOpts(
                    is_show=True, 
                    formatter=name, 
                    position="right",
                    font_size=12,
                    font_weight="bold",
                    color=colors[i % len(colors)]
                )
            )
            
        line.set_global_opts(
            title_opts=opts.TitleOpts(title="Index Performance (Base 100)", subtitle="Relative to Prev Year Close"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            # Legend at the top for fallback identification
            legend_opts=opts.LegendOpts(pos_top="5%", pos_right="5%", orient="horizontal"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(
                type_="value", 
                min_="dataMin",
                splitline_opts=opts.SplitLineOpts(is_show=True, linestyle_opts=opts.LineStyleOpts(opacity=0.1)),
            ),
            # Show full period (0-100%) by default
            datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider", range_start=0, range_end=100)],
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
