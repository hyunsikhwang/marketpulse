import json
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts


st.set_page_config(
    page_title="Global Index Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0 !important;
        max-width: 1000px !important;
    }

    [data-testid="stHeader"] {
        display: none;
    }

    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
        font-family: 'Inter', sans-serif;
    }

    .hero-container {
        padding: 1.5rem 0;
        text-align: center;
        border-bottom: 1px solid #f0f0f0;
        margin-bottom: 1.5rem;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #111111;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        font-weight: 400;
        color: #888888;
    }

    #MainMenu, footer, header, .stDeployButton {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">Global Stock Index Performance</div>
        <div class="hero-subtitle">기준일 종가를 100으로 두고 주요 지수 상대 수익률을 비교합니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

indices = {
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Russell 2000": "^RUT",
    "Dow Jones Industry": "^DJI",
    "Nikkei 225": "^N225",
    "Nifty50": "^NSEI",
    "Sensex": "^BSESN",
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "CSI 300": "000300.SS",
    "SSE STAR 50": "000688.SS",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
}


@st.cache_data(ttl=3600)
def fetch_data(indices_dict: dict[str, str]) -> pd.DataFrame:
    today = datetime.now()
    start_date = datetime(today.year - 1, 1, 1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    tickers = list(indices_dict.values())

    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        if data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex) and "Close" in data.columns.levels[0]:
            all_close = data["Close"]
        else:
            all_close = data[["Close"]] if "Close" in data.columns else data

        inv_indices = {ticker: name for name, ticker in indices_dict.items()}
        all_close = all_close.rename(columns=inv_indices).ffill()
        return all_close.sort_index()
    except Exception as exc:
        st.error(f"데이터 조회 중 오류가 발생했습니다: {exc}")
        return pd.DataFrame()


def format_metric_html(label: str, value: float, css_class: str, prefix: str = "") -> str:
    if pd.notna(value):
        return f"{label}<span class='{css_class}'>{prefix}{value:.2f}%</span>"
    return f"{label}N/A"


with st.spinner("데이터를 불러오고 있습니다..."):
    df = fetch_data(indices)

if df.empty:
    st.error("데이터를 불러오지 못했습니다.")
    st.stop()

current_year = datetime.now().year
prev_year_df = df[df.index.year == (current_year - 1)]

if prev_year_df.empty:
    st.warning(f"전년도({current_year - 1}) 데이터를 찾을 수 없습니다.")
    st.stop()

default_base_timestamp = prev_year_df.index[-1]
default_base_date = default_base_timestamp.date()

if "selected_base_date" not in st.session_state:
    st.session_state.selected_base_date = default_base_date

date_col, reset_col = st.columns([5, 1])
with reset_col:
    st.write("")
    reset_requested = st.button("Reset", use_container_width=True)

if reset_requested:
    st.session_state.selected_base_date = default_base_date

with date_col:
    selected_base_date = st.date_input(
        "기준일 선택",
        key="selected_base_date",
        min_value=df.index.min().date(),
        max_value=df.index.max().date(),
        help="휴장일을 선택하면 해당 날짜 이전의 가장 가까운 거래일 종가를 기준으로 사용합니다.",
    )

if reset_requested:
    st.rerun()

eligible_dates = df.index[df.index <= pd.Timestamp(selected_base_date)]
if len(eligible_dates) == 0:
    st.warning("선택한 기준일 이전의 거래 데이터를 찾을 수 없습니다.")
    st.stop()

effective_base_timestamp = eligible_dates[-1]
base_close_series = df.loc[effective_base_timestamp]
comparison_df = df[df.index >= effective_base_timestamp]
normalized_df = (comparison_df / base_close_series) * 100
normalized_df = normalized_df.dropna(axis=1, how="all")

if normalized_df.empty:
    st.warning("선택한 기준일로 비교할 수 있는 데이터가 없습니다.")
    st.stop()

comparison_df = comparison_df[normalized_df.columns]
latest_price_series = comparison_df.iloc[-1]
period_high_series = comparison_df.max()
period_low_series = comparison_df.min()

if effective_base_timestamp.date() != selected_base_date:
    st.caption(
        f"선택한 날짜는 휴장일이어서 기준일을 {effective_base_timestamp.strftime('%Y-%m-%d')} 종가로 적용했습니다."
    )

original_order = list(normalized_df.columns)
latest_perf_series = normalized_df.iloc[-1]
sorted_order = latest_perf_series.sort_values(ascending=False).index.tolist()

cards_html = ""
for name in original_order:
    val = latest_perf_series[name]
    period_pct = val - 100
    trend_color = "#e63946" if period_pct < 0 else "#2a9d8f"
    trend_symbol = "▼" if period_pct < 0 else "▲"
    current_price = latest_price_series.get(name)
    period_high = period_high_series.get(name)
    period_low = period_low_series.get(name)

    if pd.notna(current_price) and pd.notna(period_high) and period_high > 0:
        drawdown_from_high = ((period_high - current_price) / period_high) * 100
    else:
        drawdown_from_high = float("nan")

    if pd.notna(current_price) and pd.notna(period_low) and period_low > 0:
        rise_from_low = ((current_price - period_low) / period_low) * 100
    else:
        rise_from_low = float("nan")

    safe_id = "".join(filter(str.isalnum, name))
    drawdown_html = format_metric_html("고점 대비 ", drawdown_from_high, "metric-dd-value", prefix="-")
    rise_html = format_metric_html("저점 대비 ", rise_from_low, "metric-rise-value", prefix="+")

    cards_html += f"""
    <div class="metric-card" id="card-{safe_id}" data-name="{name}">
        <div class="metric-label">{name}</div>
        <div class="metric-value">{val:.2f}</div>
        <div class="metric-trend" style="color: {trend_color};">
            {trend_symbol} {abs(period_pct):.2f}%
        </div>
        <div class="metric-subtrend">{drawdown_html}</div>
        <div class="metric-subtrend">{rise_html}</div>
    </div>
    """

num_rows = (len(original_order) + 3) // 4
component_height = num_rows * 135 + 10

components.html(
    f"""
    <style>
    body {{
        margin: 0;
        padding: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: transparent;
        overflow: hidden;
    }}
    .metrics-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        padding: 5px;
        background-color: transparent;
    }}
    .metric-card {{
        background-color: #ffffff;
        border: 1px solid #eaeaea;
        border-radius: 12px;
        padding: 12px 15px;
        width: calc(25% - 12px);
        box-sizing: border-box;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.25s ease;
        opacity: 0;
        transform: scale(0.9);
    }}
    .metric-card.ready {{
        opacity: 1;
        transform: scale(1);
    }}
    .metric-card:hover {{
        border-color: #007aff;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.06);
        background-color: #f9f9f9;
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: #888888;
        font-weight: 600;
        margin-bottom: 2px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .metric-value {{
        font-size: 1.4rem;
        font-weight: 700;
        color: #111111;
        margin-bottom: 0;
    }}
    .metric-trend {{
        font-size: 0.85rem;
        font-weight: 600;
    }}
    .metric-subtrend {{
        font-size: 0.72rem;
        color: #6b7280;
        line-height: 1.35;
    }}
    .metric-dd-value {{
        color: #e63946;
        font-weight: 700;
    }}
    .metric-rise-value {{
        color: #2a9d8f;
        font-weight: 700;
    }}
    </style>

    <div class="metrics-container" id="grid">
        {cards_html}
    </div>

    <script>
    window.onload = function() {{
        const grid = document.getElementById('grid');
        const cards = Array.from(grid.querySelectorAll('.metric-card'));
        const sortedOrder = {json.dumps(sorted_order)};

        setTimeout(() => {{
            cards.forEach(card => card.classList.add('ready'));
        }}, 50);

        setTimeout(() => {{
            const firstRects = cards.map(card => card.getBoundingClientRect());
            const sortedCards = sortedOrder
                .map(name => cards.find(card => card.getAttribute('data-name') === name))
                .filter(Boolean);

            sortedCards.forEach(card => grid.appendChild(card));

            sortedCards.forEach(card => {{
                const name = card.getAttribute('data-name');
                const originalIndex = cards.findIndex(item => item.getAttribute('data-name') === name);
                const firstRect = firstRects[originalIndex];
                const lastRect = card.getBoundingClientRect();
                const dx = firstRect.left - lastRect.left;
                const dy = firstRect.top - lastRect.top;

                if (dx == 0 && dy == 0) {{
                    return;
                }}

                card.style.transition = 'none';
                card.style.transform = `translate(${{dx}}px, ${{dy}}px)`;

                requestAnimationFrame(() => {{
                    card.style.transition = 'transform 1s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    card.style.transform = 'translate(0, 0)';
                }});
            }});
        }}, 800);
    }};
    </script>
    """,
    height=component_height,
)

x_data = normalized_df.index.strftime("%Y-%m-%d").tolist()
line = Line(init_opts=opts.InitOpts(theme="light", height="600px", width="100%")).add_xaxis(xaxis_data=x_data)

colors = [
    "#5470c6",
    "#91cc75",
    "#fac858",
    "#ee6666",
    "#73c0de",
    "#3ba272",
    "#fc8452",
    "#9a60b4",
    "#ea7ccc",
    "#516b91",
]

for i, name in enumerate(normalized_df.columns):
    line.add_yaxis(
        series_name=name,
        y_axis=normalized_df[name].round(2).tolist(),
        symbol="none",
        is_smooth=False,
        label_opts=opts.LabelOpts(is_show=False),
        linestyle_opts=opts.LineStyleOpts(width=2),
        end_label_opts=opts.LabelOpts(
            is_show=True,
            formatter=name,
            position="right",
            font_size=12,
            font_weight="bold",
            color=colors[i % len(colors)],
        ),
    )

line.set_global_opts(
    title_opts=opts.TitleOpts(
        title="Index Performance (Base 100)",
        subtitle=f"Relative to {effective_base_timestamp.strftime('%Y-%m-%d')} Close",
    ),
    tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross", order="valueDesc"),
    legend_opts=opts.LegendOpts(is_show=False),
    xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
    yaxis_opts=opts.AxisOpts(
        type_="value",
        min_="dataMin",
        splitline_opts=opts.SplitLineOpts(
            is_show=True,
            linestyle_opts=opts.LineStyleOpts(opacity=0.3),
        ),
    ),
    datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider", range_start=0, range_end=100)],
)

line.set_series_opts(
    markline_opts=opts.MarkLineOpts(
        data=[opts.MarkLineItem(y=100, name="Base Close")],
        linestyle_opts=opts.LineStyleOpts(type_="dashed", color="gray", opacity=0.5),
    )
)

st_pyecharts(line, height="650px", key="index_chart")

with st.expander("Raw Data (Normalized)"):
    st.dataframe(normalized_df.style.format("{:.2f}"))
