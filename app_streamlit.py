#!/usr/bin/env python3
"""
Stock4N - Streamlit Interactive Dashboard
Giao diện tương tác để quản lý và xem kết quả phân tích
"""
import streamlit as st
import pandas as pd
import json
import subprocess
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Cấu hình
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
EXPORT_FILE = DATA_DIR / "export" / "db.json"

# Page config
st.set_page_config(
    page_title="Stock4N - VN Stock Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: bold;
    }
    .success-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# Hàm tiện ích
def run_command(cmd: str, description: str):
    """Chạy lệnh Docker và hiển thị progress"""
    with st.spinner(f"⏳ {description}..."):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            if result.returncode == 0:
                st.success(f"✅ {description} thành công!")
                return True, result.stdout
            else:
                st.error(f"❌ {description} thất bại!")
                st.code(result.stderr)
                return False, result.stderr
        except subprocess.TimeoutExpired:
            st.error(f"⏱️ {description} timeout (>5 phút)")
            return False, "Timeout"
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")
            return False, str(e)

def load_data():
    """Load dữ liệu từ db.json"""
    if not EXPORT_FILE.exists():
        return None

    try:
        with open(EXPORT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return None

def format_recommendation(rec: str):
    """Format màu sắc cho recommendation"""
    colors = {
        "MUA MẠNH": "🟢",
        "MUA THĂM DÒ": "🔵",
        "THEO DÕI": "🟡",
        "BÁN": "🔴"
    }
    for key, icon in colors.items():
        if key in rec:
            return f"{icon} {rec}"
    return rec

# === SIDEBAR ===
with st.sidebar:
    st.title("📈 Stock4N")
    st.markdown("### VN Stock Intelligent Advisor")
    st.markdown("---")

    st.markdown("### 🎯 Actions")

    # Action buttons
    if st.button("🔄 1. Chạy Tất Cả (All)"):
        run_command(
            "docker exec stock4n_app python src/main.py all",
            "Pipeline đầy đủ"
        )
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Ingestion"):
            run_command(
                "docker exec stock4n_app python src/main.py ingestion",
                "Lấy dữ liệu"
            )

    with col2:
        if st.button("⚙️ Processing"):
            run_command(
                "docker exec stock4n_app python src/main.py processing",
                "Xử lý dữ liệu"
            )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧠 Analysis"):
            run_command(
                "docker exec stock4n_app python src/main.py analysis",
                "Phân tích"
            )

    with col2:
        if st.button("💼 Portfolio"):
            run_command(
                "docker exec stock4n_app python src/main.py portfolio",
                "Tạo danh mục"
            )

    if st.button("📦 Export"):
        run_command(
            "docker exec stock4n_app python src/main.py export",
            "Xuất db.json"
        )
        st.rerun()

    st.markdown("---")

    if st.button("🔄 Sync Frontend"):
        run_command(
            "python scripts/sync_data.py",
            "Đồng bộ db.json sang frontend"
        )
        st.success("✅ Frontend đã được cập nhật!")

    st.markdown("---")

    # Docker status
    st.markdown("### 🐳 Docker Status")
    result = subprocess.run(
        "docker ps --filter name=stock4n_app --format '{{.Status}}'",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        st.success(f"✅ Running\n{result.stdout.strip()}")
    else:
        st.error("❌ Container không chạy")
        if st.button("▶️ Khởi động Docker"):
            run_command("docker-compose up -d", "Khởi động container")

# === MAIN CONTENT ===
st.title("📊 Stock4N Dashboard")

# Load data
data = load_data()

if data is None:
    st.warning("⚠️ Chưa có dữ liệu. Hãy chạy pipeline bằng nút **'Chạy Tất Cả'** ở sidebar.")
    st.info("""
    ### 🚀 Hướng dẫn bắt đầu:
    1. Nhấn nút **"🔄 Chạy Tất Cả (All)"** ở sidebar
    2. Đợi khoảng 2-3 phút để hệ thống lấy và phân tích dữ liệu
    3. Dashboard sẽ tự động cập nhật kết quả
    """)
    st.stop()

# Stats cards
last_updated = data.get('last_updated', 'N/A')
analysis = data.get('analysis', [])
portfolio = data.get('portfolio', [])

st.markdown(f"**Cập nhật lần cuối**: {last_updated}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📈 Tổng Số Mã",
        len(analysis),
        help="Tổng số cổ phiếu đã phân tích"
    )

with col2:
    buy_signals = len([x for x in analysis if "MUA" in x.get('Recommendation', '')])
    st.metric(
        "✅ Tín Hiệu Mua",
        buy_signals,
        help="Số mã có khuyến nghị MUA"
    )

with col3:
    strong_buy = len([x for x in analysis if "MUA MẠNH" in x.get('Recommendation', '')])
    st.metric(
        "🚀 Mua Mạnh",
        strong_buy,
        help="Số mã có khuyến nghị MUA MẠNH"
    )

with col4:
    total_capital = sum([float(x.get('Capital_VND', '0').replace(',', '')) for x in portfolio])
    st.metric(
        "💰 Vốn Phân Bổ",
        f"{total_capital/1_000_000:.1f}M",
        help="Tổng vốn đã phân bổ (triệu VND)"
    )

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["💼 Danh Mục Đầu Tư", "📊 Phân Tích Thị Trường", "📈 Biểu Đồ", "🔬 Backtest"])

# === TAB 1: Portfolio ===
with tab1:
    st.header("💼 Danh Mục Đầu Tư Khuyến Nghị")

    if not portfolio:
        st.warning("⚠️ Chưa có danh mục đầu tư. Chạy **Portfolio** ở sidebar.")
    else:
        df_portfolio = pd.DataFrame(portfolio)

        # Format columns
        df_display = df_portfolio.copy()
        df_display['Action'] = df_display['Action'].apply(format_recommendation)

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )

        # Download button
        csv = df_portfolio.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "⬇️ Tải xuống CSV",
            csv,
            "portfolio.csv",
            "text/csv",
            key='download-portfolio'
        )

# === TAB 2: Market Analysis ===
with tab2:
    st.header("📊 Phân Tích Thị Trường")

    if not analysis:
        st.warning("⚠️ Chưa có dữ liệu phân tích. Chạy **Analysis** ở sidebar.")
    else:
        df_analysis = pd.DataFrame(analysis)

        # Filters
        col1, col2 = st.columns(2)

        with col1:
            recommendations = ["Tất cả"] + sorted(df_analysis['Recommendation'].unique().tolist())
            selected_rec = st.selectbox("Lọc theo khuyến nghị", recommendations)

        with col2:
            min_score = st.slider("Điểm tối thiểu", 0.0, 10.0, 0.0, 0.1)

        # Apply filters
        df_filtered = df_analysis.copy()
        if selected_rec != "Tất cả":
            df_filtered = df_filtered[df_filtered['Recommendation'] == selected_rec]
        df_filtered = df_filtered[df_filtered['Total_Score'] >= min_score]

        # Sort by score
        df_filtered = df_filtered.sort_values('Total_Score', ascending=False)

        # Display
        st.markdown(f"**Kết quả**: {len(df_filtered)} mã")

        df_display = df_filtered.copy()
        df_display['Recommendation'] = df_display['Recommendation'].apply(format_recommendation)

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )

        # Download button
        csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "⬇️ Tải xuống CSV",
            csv,
            "analysis.csv",
            "text/csv",
            key='download-analysis'
        )

# === TAB 3: Charts ===
with tab3:
    st.header("📈 Biểu Đồ & Thống Kê")

    if not analysis:
        st.warning("⚠️ Chưa có dữ liệu. Chạy pipeline ở sidebar.")
    else:
        df_analysis = pd.DataFrame(analysis)

        # Chart 1: Recommendation distribution
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Phân Bố Khuyến Nghị")
            rec_counts = df_analysis['Recommendation'].value_counts()

            fig = px.pie(
                values=rec_counts.values,
                names=rec_counts.index,
                title="Số lượng mã theo khuyến nghị",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Phân Bố Điểm Số")
            fig = px.histogram(
                df_analysis,
                x='Total_Score',
                nbins=20,
                title="Histogram điểm số",
                labels={'Total_Score': 'Điểm số', 'count': 'Số lượng'}
            )
            st.plotly_chart(fig, use_container_width=True)

        # Chart 2: Top stocks
        st.subheader("Top 10 Cổ Phiếu Tiềm Năng")
        top10 = df_analysis.nlargest(10, 'Total_Score')

        fig = go.Figure(data=[
            go.Bar(
                x=top10['Symbol'],
                y=top10['Total_Score'],
                text=top10['Total_Score'].round(1),
                textposition='auto',
                marker_color='lightblue'
            )
        ])
        fig.update_layout(
            title="Top 10 theo điểm số",
            xaxis_title="Mã CK",
            yaxis_title="Điểm số",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        # Chart 3: Fund vs Tech score
        st.subheader("Phân Tích Cơ Bản vs Kỹ Thuật")
        fig = px.scatter(
            df_analysis,
            x='Fund_Score',
            y='Tech_Score',
            size='Total_Score',
            color='Recommendation',
            hover_data=['Symbol'],
            title="Scatter plot: Điểm cơ bản vs kỹ thuật",
            labels={
                'Fund_Score': 'Điểm Cơ Bản',
                'Tech_Score': 'Điểm Kỹ Thuật'
            }
        )
        st.plotly_chart(fig, use_container_width=True)

# === TAB 4: Backtest ===
with tab4:
    st.header("🔬 Backtest Chiến Lược")

    st.markdown("""
    Backtest mô phỏng giao dịch dựa trên chiến lược scoring của Stock4N.

    **Chiến lược**:
    - 🟢 **Mua**: Score >= min_score + Khuyến nghị "MUA"
    - 🔴 **Bán**: Stop loss (-7%), Take profit (+15%), hoặc hết kỳ
    - 💼 **Quản lý vốn**: 10% mỗi vị thế, tối đa 10 vị thế
    """)

    st.markdown("---")

    # Backtest parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        lookback_days = st.number_input(
            "📅 Số ngày quay lại",
            min_value=30,
            max_value=730,
            value=365,
            step=30,
            help="Số ngày lịch sử để test (365 = 1 năm)"
        )

    with col2:
        min_score = st.number_input(
            "⭐ Điểm tối thiểu",
            min_value=0.0,
            max_value=10.0,
            value=6.0,
            step=0.5,
            help="Điểm tối thiểu để mua cổ phiếu"
        )

    with col3:
        initial_capital = st.number_input(
            "💰 Vốn ban đầu (VND)",
            min_value=10_000_000,
            max_value=10_000_000_000,
            value=100_000_000,
            step=10_000_000,
            help="Vốn khởi đầu (VND)"
        )

    # Run backtest button
    if st.button("🚀 Chạy Backtest", type="primary", use_container_width=True):
        cmd = f"docker exec stock4n_app python src/main.py backtest --days {lookback_days} --score {min_score} --capital {initial_capital}"
        success, output = run_command(cmd, "Chạy backtest")

        if success:
            st.code(output, language="text")

    st.markdown("---")

    # Load backtest results
    backtest_dir = DATA_DIR / "backtest"

    if not backtest_dir.exists():
        st.info("💡 Chưa có kết quả backtest. Nhấn nút **'Chạy Backtest'** để bắt đầu.")
    else:
        # Find latest backtest result
        result_files = sorted(backtest_dir.glob("backtest_trades_*.csv"), reverse=True)

        if not result_files:
            st.info("💡 Chưa có kết quả backtest. Nhấn nút **'Chạy Backtest'** để bắt đầu.")
        else:
            latest_result = result_files[0]

            try:
                # Load trades
                df_trades = pd.read_csv(latest_result)

                # Load summary if exists
                summary_file = latest_result.with_suffix('.txt')
                summary_text = ""
                if summary_file.exists():
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_text = f.read()

                st.success(f"✅ Kết quả mới nhất: {latest_result.name}")

                # Display summary
                if summary_text:
                    st.subheader("📊 Tổng Kết")
                    st.text(summary_text)

                st.markdown("---")

                # Performance metrics from summary
                if not df_trades.empty:
                    # Calculate basic metrics
                    total_trades = len(df_trades)
                    buy_trades = df_trades[df_trades['action'] == 'BUY']
                    sell_trades = df_trades[df_trades['action'] == 'SELL']

                    if not sell_trades.empty and 'pnl' in sell_trades.columns:
                        total_pnl = sell_trades['pnl'].sum()
                        wins = len(sell_trades[sell_trades['pnl'] > 0])
                        losses = len(sell_trades[sell_trades['pnl'] < 0])
                        win_rate = (wins / len(sell_trades) * 100) if len(sell_trades) > 0 else 0

                        # Metrics cards
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("💼 Tổng Giao Dịch", total_trades)

                        with col2:
                            st.metric("💵 P&L Tổng", f"{total_pnl/1_000_000:.1f}M VND")

                        with col3:
                            st.metric("🎯 Tỷ Lệ Thắng", f"{win_rate:.1f}%")

                        with col4:
                            st.metric("✅ Thắng / ❌ Thua", f"{wins} / {losses}")

                st.markdown("---")

                # Trades table
                st.subheader("📋 Chi Tiết Giao Dịch")

                # Filter trades
                trade_type = st.radio(
                    "Lọc theo loại",
                    ["Tất cả", "Mua (BUY)", "Bán (SELL)"],
                    horizontal=True
                )

                df_display = df_trades.copy()
                if trade_type == "Mua (BUY)":
                    df_display = df_display[df_display['action'] == 'BUY']
                elif trade_type == "Bán (SELL)":
                    df_display = df_display[df_display['action'] == 'SELL']

                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )

                # Download button
                csv = df_trades.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "⬇️ Tải xuống kết quả CSV",
                    csv,
                    f"backtest_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key='download-backtest'
                )

                # Visualizations
                if not sell_trades.empty and 'pnl' in sell_trades.columns:
                    st.markdown("---")
                    st.subheader("📈 Trực Quan Hóa")

                    col1, col2 = st.columns(2)

                    with col1:
                        # P&L distribution
                        st.markdown("**Phân Bố P&L**")
                        fig = px.histogram(
                            sell_trades,
                            x='pnl',
                            nbins=20,
                            title="Histogram P&L các giao dịch",
                            labels={'pnl': 'P&L (VND)', 'count': 'Số lượng'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        # Win/Loss by stock
                        st.markdown("**Top P&L Theo Mã**")
                        pnl_by_symbol = sell_trades.groupby('symbol')['pnl'].sum().sort_values(ascending=False).head(10)

                        fig = go.Figure(data=[
                            go.Bar(
                                x=pnl_by_symbol.index,
                                y=pnl_by_symbol.values / 1_000_000,
                                marker_color=['green' if x > 0 else 'red' for x in pnl_by_symbol.values]
                            )
                        ])
                        fig.update_layout(
                            title="Top 10 P&L theo mã CK (triệu VND)",
                            xaxis_title="Mã CK",
                            yaxis_title="P&L (triệu VND)",
                            showlegend=False
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Cumulative P&L over time
                    if 'date' in sell_trades.columns:
                        st.markdown("**Đường Cong P&L Tích Lũy**")
                        df_cum = sell_trades.copy()
                        df_cum['date'] = pd.to_datetime(df_cum['date'])
                        df_cum = df_cum.sort_values('date')
                        df_cum['cumulative_pnl'] = df_cum['pnl'].cumsum()

                        fig = px.line(
                            df_cum,
                            x='date',
                            y='cumulative_pnl',
                            title="P&L tích lũy theo thời gian",
                            labels={'date': 'Ngày', 'cumulative_pnl': 'P&L Tích Lũy (VND)'}
                        )
                        fig.add_hline(y=0, line_dash="dash", line_color="gray")
                        st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Lỗi đọc kết quả backtest: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Stock4N - VN Stock Intelligent Advisor</p>
    <p style='font-size: 0.8em;'>⚠️ Đây không phải lời khuyên đầu tư. Luôn tự nghiên cứu trước khi đầu tư.</p>
</div>
""", unsafe_allow_html=True)
