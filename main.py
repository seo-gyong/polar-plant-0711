import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# =============================
# 기본 설정
# =============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =============================
# 한글 폰트 CSS (Streamlit)
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 상수 정의
# =============================
DATA_DIR = Path("data")

SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# =============================
# 유틸: NFC/NFD 파일 찾기
# =============================
def find_file_by_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for file in directory.iterdir():
        name_nfc = unicodedata.normalize("NFC", file.name)
        name_nfd = unicodedata.normalize("NFD", file.name)
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return file
    return None

# =============================
# 데이터 로딩
# =============================
@st.cache_data
def load_env_data():
    env_data = {}
    for school in SCHOOL_EC.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_name(DATA_DIR, filename)
        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {filename}")
            return None
        df = pd.read_csv(file_path)
        df["학교"] = school
        env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data():
    xlsx_name = "4개교_생육결과데이터.xlsx"
    file_path = find_file_by_name(DATA_DIR, xlsx_name)
    if file_path is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(file_path)
    data = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["학교"] = sheet
        df["EC"] = SCHOOL_EC.get(sheet)
        data[sheet] = df
    return data

# =============================
# 데이터 로딩 UI
# =============================
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# =============================
# 제목
# =============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# =============================
# 사이드바
# =============================
school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + list(SCHOOL_EC.keys())
)

# =============================
# 탭 구성
# =============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# Tab 1: 실험 개요
# =====================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown(
        """
        극지 환경에서의 식물 생육은 **양액 EC 농도**에 크게 영향을 받습니다.  
        본 연구는 **서로 다른 EC 조건**에서 극지식물의 생육 반응을 비교하여  
        **최적 EC 농도**를 도출하는 것을 목표로 합니다.
        """
    )

    info_df = pd.DataFrame({
        "학교": SCHOOL_EC.keys(),
        "EC 목표": SCHOOL_EC.values(),
        "개체수": [len(growth_data[s]) for s in SCHOOL_EC.keys()],
        "색상": [SCHOOL_COLOR[s] for s in SCHOOL_EC.keys()]
    })

    st.dataframe(info_df, use_container_width=True)

    total_count = sum(len(growth_data[s]) for s in growth_data)
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()
    optimal_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", f"{total_count} 개")
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", f"{optimal_ec}")

# =====================================================
# Tab 2: 환경 데이터
# =====================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": SCHOOL_EC[school]
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "EC 비교"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["target_ec"], name="목표 EC", row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("환경 시계열 데이터")

    if school_option != "전체":
        df = env_data[school_option]

        fig_ts = go.Figure()
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(y=SCHOOL_EC[school_option], line_dash="dot", name="목표 EC")

        fig_ts.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📂 환경 데이터 원본"):
        all_env_df = pd.concat(env_data.values())
        st.dataframe(all_env_df)

        csv_buffer = io.BytesIO()
        all_env_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=csv_buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# =====================================================
# Tab 3: 생육 결과
# =====================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    growth_all = pd.concat(growth_data.values())

    ec_weight = growth_all.groupby("EC")["생중량(g)"].mean().reset_index()
    best_ec = ec_weight.loc[ec_weight["생중량(g)"].idxmax(), "EC"]

    st.metric("최적 EC (최대 생중량)", f"{best_ec}")

    fig_w = px.bar(
        ec_weight,
        x="EC",
        y="생중량(g)",
        text_auto=".2f"
    )
    fig_w.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_w, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    fig_box = px.box(
        growth_all,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")

    c1, c2 = st.columns(2)

    with c1:
        fig_sc1 = px.scatter(
            growth_all,
            x="잎 수(장)",
            y="생중량(g)",
            color="학교"
        )
        fig_sc1.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_sc1, use_container_width=True)

    with c2:
        fig_sc2 = px.scatter(
            growth_all,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="학교"
        )
        fig_sc2.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📂 생육 데이터 원본 다운로드"):
        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
