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
tab1, tab2, tab3 = st.tabs(["💼 Danh Mục Đầu Tư", "📊 Phân Tích Thị Trường", "📈 Biểu Đồ"])

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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Stock4N - VN Stock Intelligent Advisor</p>
    <p style='font-size: 0.8em;'>⚠️ Đây không phải lời khuyên đầu tư. Luôn tự nghiên cứu trước khi đầu tư.</p>
</div>
""", unsafe_allow_html=True)
