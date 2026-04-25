import json
import logging
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from io import StringIO

import pandas as pd
import streamlit as st
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

HISTORY_START_DATE = "2000-01-01"
MIN_SELECTABLE_DATE = date(1900, 1, 1)
TICKER_START_DATES = {
    "000688.SS": "2020-07-23",
}


def resolve_ticker_start_date(ticker: str, default_start_date: str) -> str:
    ticker_start_date = TICKER_START_DATES.get(ticker)
    if not ticker_start_date:
        return default_start_date
    return max(default_start_date, ticker_start_date)


def download_history(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    effective_start_date = resolve_ticker_start_date(ticker, start_date)
    sink = StringIO()
    yf_logger = logging.getLogger("yfinance")
    previous_level = yf_logger.level

    try:
        yf_logger.setLevel(logging.CRITICAL)
        with redirect_stdout(sink), redirect_stderr(sink):
            data = yf.download(
                ticker,
                start=effective_start_date,
                end=end_date,
                progress=False,
                threads=False,
            )
        if not data.empty:
            return data

        with redirect_stdout(sink), redirect_stderr(sink):
            return yf.Ticker(ticker).history(
                start=effective_start_date,
                end=end_date,
                auto_adjust=False,
                actions=False,
            )
    except Exception:
        return pd.DataFrame()
    finally:
        yf_logger.setLevel(previous_level)


def extract_close_series(data: pd.DataFrame, name: str) -> pd.Series | None:
    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.levels[0]:
            return None
        close_data = data["Close"]
        if isinstance(close_data, pd.DataFrame):
            if close_data.shape[1] == 0:
                return None
            close_series = close_data.iloc[:, 0]
        else:
            close_series = close_data
    else:
        if "Close" not in data.columns:
            return None
        close_series = data["Close"]

    if not isinstance(close_series, pd.Series):
        if len(data.index) != 1:
            return None
        close_series = pd.Series([close_series], index=data.index)

    close_series = close_series.rename(name)
    if close_series.dropna().empty:
        return None
    return close_series


@st.cache_data(ttl=3600)
def fetch_data(indices_dict: dict[str, str]) -> tuple[pd.DataFrame, list[str]]:
    today = datetime.now()
    start_date = HISTORY_START_DATE
    end_date = today.strftime("%Y-%m-%d")
    close_frames: list[pd.Series] = []
    failed_indices: list[str] = []

    try:
        for name, ticker in indices_dict.items():
            data = download_history(ticker, start_date, end_date)
            close_series = extract_close_series(data, name)
            if close_series is None:
                failed_indices.append(name)
                continue

            close_frames.append(close_series)

        if not close_frames:
            return pd.DataFrame(), failed_indices

        all_close = pd.concat(close_frames, axis=1, sort=False).sort_index().ffill()
        return all_close, failed_indices
    except Exception as exc:
        st.error(f"데이터 조회 중 오류가 발생했습니다: {exc}")
        return pd.DataFrame(), list(indices_dict.keys())


def format_metric_html(label: str, value: float, css_class: str, prefix: str = "") -> str:
    if pd.notna(value):
        return f"{label}<span class='{css_class}'>{prefix}{value:.2f}%</span>"
    return f"{label}N/A"


with st.spinner("데이터를 불러오고 있습니다..."):
    df, failed_indices = fetch_data(indices)

if df.empty:
    st.error("데이터를 불러오지 못했습니다.")
    st.stop()

if failed_indices:
    st.caption(f"가격 데이터를 불러오지 못한 지수는 제외했습니다: {', '.join(failed_indices)}")

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
        min_value=MIN_SELECTABLE_DATE,
        max_value=df.index.max().date(),
        help="휴장일을 선택하면 해당 날짜 이전의 가장 가까운 거래일 종가를 기준으로 사용합니다.",
    )

if reset_requested:
    st.rerun()

selected_base_timestamp = pd.Timestamp(selected_base_date)
history_until_selected = df.loc[df.index <= selected_base_timestamp]

if history_until_selected.empty:
    base_close_series = df.ffill().iloc[0]
    comparison_df = df.copy()
else:
    base_close_series = history_until_selected.ffill().iloc[-1]
    comparison_df = df[df.index >= selected_base_timestamp]
    if comparison_df.empty:
        comparison_df = df[df.index >= history_until_selected.index[-1]]

base_close_series = base_close_series.dropna()
comparison_df = comparison_df[base_close_series.index]
normalized_df = (comparison_df / base_close_series) * 100
normalized_df = normalized_df.dropna(axis=1, how="all")

if normalized_df.empty:
    st.warning("선택한 기준일로 비교할 수 있는 데이터가 없습니다.")
    st.stop()

comparison_df = comparison_df[normalized_df.columns]
latest_price_series = comparison_df.iloc[-1]
period_high_series = comparison_df.max()
period_low_series = comparison_df.min()

if history_until_selected.empty:
    earliest_available_date = df.index.min().strftime("%Y-%m-%d")
    st.caption(
        f"선택한 날짜 이전 데이터가 없어 가장 이른 거래일인 {earliest_available_date} 종가를 기준으로 적용했습니다."
    )
else:
    fallback_count = 0
    for column in normalized_df.columns:
        valid_dates = history_until_selected[column].dropna().index
        if len(valid_dates) == 0 or valid_dates[-1].date() != selected_base_date:
            fallback_count += 1

    if fallback_count:
        st.caption(
            f"선택한 날짜에 종가가 없는 지수 {fallback_count}개는 각 지수의 직전 거래일 종가를 기준으로 적용했습니다."
        )

original_order = list(normalized_df.columns)
latest_perf_series = normalized_df.iloc[-1]
sorted_order = latest_perf_series.sort_values(ascending=False).index.tolist()

metric_cards: list[dict[str, str | float]] = []
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

    drawdown_html = format_metric_html("고점 대비 ", drawdown_from_high, "metric-dd-value", prefix="-")
    rise_html = format_metric_html("저점 대비 ", rise_from_low, "metric-rise-value", prefix="+")
    metric_cards.append(
        {
            "name": name,
            "value": val,
            "trend_color": trend_color,
            "trend_symbol": trend_symbol,
            "period_pct": abs(period_pct),
            "drawdown_html": drawdown_html,
            "rise_html": rise_html,
            "safe_id": "".join(filter(str.isalnum, name)),
        }
    )

cards_html = ""
for card in metric_cards:
    cards_html += f"""
    <div class="metric-card" id="card-{card["safe_id"]}" data-name="{card["name"]}">
        <div class="metric-label">{card["name"]}</div>
        <div class="metric-value">{card["value"]:.2f}</div>
        <div class="metric-trend" style="color: {card["trend_color"]};">
            {card["trend_symbol"]} {card["period_pct"]:.2f}%
        </div>
        <div class="metric-subtrend">{card["drawdown_html"]}</div>
        <div class="metric-subtrend">{card["rise_html"]}</div>
    </div>
    """

card_markup = f"""
<style>
.metrics-container {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    padding: 5px 0;
}}
@media (max-width: 1100px) {{
    .metrics-container {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}
@media (max-width: 640px) {{
    .metrics-container {{
        grid-template-columns: 1fr;
    }}
}}
.metric-card {{
    background-color: #ffffff;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 12px 15px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    min-height: 118px;
    box-sizing: border-box;
    opacity: 0;
    transform: scale(0.92);
    transition:
        transform 0.85s cubic-bezier(0.34, 1.56, 0.64, 1),
        opacity 0.35s ease,
        border-color 0.25s ease,
        box-shadow 0.25s ease,
        background-color 0.25s ease;
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
<div class="metrics-container" id="metrics-grid">
    {cards_html}
</div>
<script>
(() => {{
    const grid = document.getElementById("metrics-grid");
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll(".metric-card"));
    const sortedOrder = {json.dumps(sorted_order)};

    requestAnimationFrame(() => {{
        cards.forEach((card, index) => {{
            setTimeout(() => card.classList.add("ready"), index * 35);
        }});
    }});

    setTimeout(() => {{
        const firstRects = new Map(cards.map((card) => [card.dataset.name, card.getBoundingClientRect()]));
        const sortedCards = sortedOrder
            .map((name) => cards.find((card) => card.dataset.name === name))
            .filter(Boolean);

        sortedCards.forEach((card) => grid.appendChild(card));

        sortedCards.forEach((card) => {{
            const firstRect = firstRects.get(card.dataset.name);
            const lastRect = card.getBoundingClientRect();
            if (!firstRect || !lastRect) return;

            const dx = firstRect.left - lastRect.left;
            const dy = firstRect.top - lastRect.top;
            if (dx === 0 && dy === 0) return;

            card.style.transition = "none";
            card.style.transform = `translate(${{dx}}px, ${{dy}}px) scale(1)`;

            requestAnimationFrame(() => {{
                card.style.transition = "transform 0.95s cubic-bezier(0.22, 1, 0.36, 1)";
                card.style.transform = "translate(0, 0) scale(1)";
            }});
        }});
    }}, 700);
}})();
</script>
"""

html_renderer = getattr(st, "html", None)
chart_width_style = """
<style>
.chart-full-width {
    width: min(1240px, calc(100vw - 3rem));
    margin-left: 50%;
    transform: translateX(-50%);
}
@media (max-width: 1300px) {
    .chart-full-width {
        width: 100%;
        margin-left: 0;
        transform: none;
    }
}
</style>
"""
st.markdown(chart_width_style, unsafe_allow_html=True)

if callable(html_renderer):
    html_renderer(card_markup, unsafe_allow_javascript=True)
else:
    st.markdown(card_markup, unsafe_allow_html=True)

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
        subtitle=f"Relative to {selected_base_date:%Y-%m-%d} or latest prior close by index",
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

st.markdown('<div class="chart-full-width">', unsafe_allow_html=True)
st_pyecharts(line, height="650px", key="index_chart")
st.markdown("</div>", unsafe_allow_html=True)

with st.expander("Raw Data (Normalized)"):
    st.dataframe(normalized_df.style.format("{:.2f}"))
