import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# =====================================================
# 기본 설정
# =====================================================
st.set_page_config(
    page_title="나도수영의 환경 분석",
    layout="wide"
)

# =====================================================
# 한글 폰트 (Streamlit)
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 상수
# =====================================================
DATA_DIR = Path("data")

SCHOOL_EC = {
    "송도고": 2.0,   # 최적
    "하늘고": 4.0,
    "아라고": 8.0,
    "동산고": 1.0
}

# =====================================================
# NFC / NFD 안전 파일 찾기
# =====================================================
def find_file(directory: Path, target: str):
    t_nfc = unicodedata.normalize("NFC", target)
    t_nfd = unicodedata.normalize("NFD", target)

    for f in directory.iterdir():
        f_nfc = unicodedata.normalize("NFC", f.name)
        f_nfd = unicodedata.normalize("NFD", f.name)
        if f_nfc == t_nfc or f_nfd == t_nfd:
            return f
    return None

# =====================================================
# 데이터 로딩
# =====================================================
@st.cache_data
def load_env():
    result = {}
    for school in SCHOOL_EC:
        fname = f"{school}_환경데이터.csv"
        path = find_file(DATA_DIR, fname)
        if path is None:
            st.error(f"환경 데이터 파일 없음: {fname}")
            return None
        df = pd.read_csv(path)
        df["학교"] = school
        result[school] = df
    return result

@st.cache_data
def load_growth():
    path = find_file(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if path is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(path)
    data = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["학교"] = sheet
        df["EC"] = SCHOOL_EC.get(sheet)
        data[sheet] = df
    return data

# =====================================================
# 로딩
# =====================================================
with st.spinner("📂 데이터 불러오는 중..."):
    env_data = load_env()
    growth_data = load_growth()

if env_data is None or growth_data is None:
    st.stop()

env_all = pd.concat(env_data.values())
growth_all = pd.concat(growth_data.values())

# =====================================================
# 제목 & 사이드바
# =====================================================
st.title("🌱 나도수영의 환경 분석")

school_choice = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + list(SCHOOL_EC.keys())
)

# =====================================================
# 탭 구성
# =====================================================
tab1, tab2, tab3 = st.tabs([
    "📐 EC 2 최적성 증명",
    "🌡️ 환경 요인 상관관계",
    "🌱 온도 vs 생육"
])

# =====================================================
# TAB 1 — 레이더 차트 (EC 2 vs EC 8)
# =====================================================
with tab1:
    st.subheader("왜 EC 2.0이 최적인가? (환경 + 생육 형태 비교)")

    compare_schools = ["송도고", "아라고"]

    radar_rows = []
    for s in compare_schools:
        env_mean = env_data[s][["temperature", "humidity", "ph", "ec"]].mean()
        grow_mean = growth_data[s][["잎 수(장)", "지상부 길이(mm)", "생중량(g)"]].mean()

        radar_rows.append(pd.concat([env_mean, grow_mean], axis=0))

    radar_df = pd.DataFrame(radar_rows, index=compare_schools)

    fig_radar = go.Figure()
    for school in radar_df.index:
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_df.loc[school],
            theta=radar_df.columns,
            fill="toself",
            name=school
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig_radar, use_container_width=True)

    st.info("📌 EC 8(아라고)는 생육 수치뿐 아니라 환경 밸런스 자체가 무너진 형태를 보임")

# =====================================================
# TAB 2 — 습도 vs EC vs 생중량 (이중축)
# =====================================================
with tab2:
    st.subheader("아라고 생육 부진 원인: EC + 과도한 습도")

    summary = []
    for s in SCHOOL_EC:
        summary.append({
            "학교": s,
            "평균 습도": env_data[s]["humidity"].mean(),
            "EC": SCHOOL_EC[s],
            "평균 생중량": growth_data[s]["생중량(g)"].mean()
        })

    sum_df = pd.DataFrame(summary)

    fig_mix = make_subplots(specs=[[{"secondary_y": True}]])

    fig_mix.add_bar(
        x=sum_df["학교"],
        y=sum_df["평균 습도"],
        name="평균 습도 (%)",
        secondary_y=False
    )

    fig_mix.add_scatter(
        x=sum_df["학교"],
        y=sum_df["평균 생중량"],
        name="평균 생중량(g)",
        secondary_y=True,
        mode="lines+markers"
    )

    fig_mix.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig_mix, use_container_width=True)

    st.warning("⚠️ 아라고는 EC 8 + 습도 69% → 뿌리 스트레스 누적")

# =====================================================
# TAB 3 — 온도와 생육 상관
# =====================================================
with tab3:
    st.subheader("의외의 결과: 비교적 높은 온도에서 생육 향상")

    temp_df = env_all.groupby("학교")["temperature"].mean().reset_index()
    weight_df = growth_all.groupby("학교")["생중량(g)"].mean().reset_index()

    merged = pd.merge(temp_df, weight_df, on="학교")

    fig_scatter = px.scatter(
        merged,
        x="temperature",
        y="생중량(g)",
        text="학교",
        size="생중량(g)"
    )

    fig_scatter.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

    st.success("✅ 극지식물은 **저온보다 안정된 중온 환경**에서 더 잘 성장")

# =====================================================
# 데이터 다운로드
# =====================================================
with st.expander("📥 생육 데이터 XLSX 다운로드"):
    buffer = io.BytesIO()
    growth_all.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "다운로드",
        data=buffer,
        file_name="생육결과_통합.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

