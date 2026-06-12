import sys
from pathlib import Path
import streamlit as st
import datetime

# 프로젝트 루트 경로를 sys.path에 추가하여 backend 패키지를 임포트 가능하도록 설정
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 백엔드 엔진 임포트 (단일 프로세스 실행 및 빠른 통신 지원)
from backend.database import db_manager
from backend.mock_data import initialize_mock_data
from backend.services.analyzer import spatial_analyzer
from backend.services.airkorea import airkorea_client

# 프론트엔드 컴포넌트 임포트
from frontend.components.map import render_pollution_map, TYPE_TRANSLATION
from frontend.components.charts import (
    render_source_type_pie,
    render_distance_pollution_scatter,
    render_pollutant_multi_bar
)

# 1. Streamlit 앱 페이지 기본 설정
st.set_page_config(
    page_title="EcoMap",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 프리미엄 Dark Theme 및 Glassmorphism UI 스타일 정의 (CSS 인젝션)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap');
    
    /* 폰트 지정 */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Malgun Gothic', sans-serif;
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        background: linear-gradient(135deg, #e74c3c, #f1c40f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        font-size: 1.1rem;
        color: #b0bec5;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* 프리미엄 카드 디자인 */
    .metric-card {
        background: rgba(30, 30, 40, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(4px);
        transition: transform 0.2s, border-color 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(231, 76, 60, 0.4);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #90a4ae;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    /* 세부사항 패널 스타일 */
    .detail-panel {
        background: rgba(22, 22, 29, 0.85);
        border-left: 4px solid #e74c3c;
        border-radius: 4px 12px 12px 4px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터베이스 상태 체크 및 자동 초기 샘플 데이터 적재
db_status = "Fallback DB" if db_manager.is_fallback else "MongoDB Atlas"
sources = db_manager.find("pollution_sources")
stations = db_manager.find("air_quality_stations")

if not sources or not stations:
    with st.spinner("🚀 초기 모의 대기질 및 측정소 데이터를 적재하고 있습니다..."):
        initialize_mock_data()
        
        # 기존에 기동해둔 위성 TIF 공간 영역이 누락되지 않도록 임포터 자동 재가동
        from backend.services.importer import GeospatialImporter
        importer = GeospatialImporter()
        importer.run_import()
        
        sources = db_manager.find("pollution_sources")
        stations = db_manager.find("air_quality_stations")
        st.rerun()

# 4. 사이드바 구성 (고급 필터링 영역)
st.sidebar.markdown(f"<div style='text-align: center; margin-bottom: 1.5rem;'><h2 style='font-family:Outfit; font-weight:800; background: linear-gradient(135deg, #00c6ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🛰️ ECO-MAP SYSTEM</h2><span style='font-size:11px; color:#888;'>DB Mode: {db_status}</span></div>", unsafe_allow_html=True)

# 산단 구역 선택
regions = ["전체", "시화반월단지", "울산석유화학단지", "여수국가산단", "대산석유화학단지", "광양국가산단"]
selected_region = st.sidebar.selectbox("🗺️ 분석 대상 국가산업단지", regions)

# 배출원 타입 필터
source_types = ["전체", "stack", "factory_roof", "waste_treatment", "agricultural", "satellite_area"]
type_labels = {"전체": "전체 보기", "stack": "굴뚝 배출원 (Stack)", "factory_roof": "공장 지붕 (Roof)", "waste_treatment": "폐기물 구역", "agricultural": "농축산 지역", "satellite_area": "위성 관측 구역 (TIF)"}
selected_type = st.sidebar.selectbox(
    "🔥 배출원 유형 필터",
    source_types,
    format_func=lambda x: type_labels[x]
)

# AI 신뢰도 임계값 슬라이더
min_conf = st.sidebar.slider("📊 위성 탐지 최소 신뢰도 (%)", min_value=50, max_value=100, value=70, step=5) / 100.0

# 분석 반경 임계값 슬라이더
radius_km = st.sidebar.slider("📏 배출원 영향 분석 반경 (km)", min_value=1.0, max_value=15.0, value=6.0, step=0.5)

st.sidebar.markdown("---")
# 공공데이터포털 에어코리아 API 상태 표시
api_status_html = """
<div style='background: rgba(30, 200, 100, 0.1); border: 1px solid rgba(30, 200, 100, 0.3); border-radius: 8px; padding: 10px; font-size:12px;'>
    <div style='color: #2ecc71; font-weight: bold;'>📡 AirKorea API 연동 모드</div>
    <div style='color: #eee; margin-top: 5px;'>인증키 미등록 상태로, 대한민국 실측 데이터 기반 고정밀 모의 시뮬레이터가 작동 중입니다. (.env에서 등록 가능)</div>
</div>
"""
if airkorea_client.is_configured:
    api_status_html = """
    <div style='background: rgba(52, 152, 219, 0.15); border: 1px solid rgba(52, 152, 219, 0.4); border-radius: 8px; padding: 10px; font-size:12px;'>
        <div style='color: #3498db; font-weight: bold;'>📡 AirKorea API 연동 모드</div>
        <div style='color: #eee; margin-top: 5px;'>환경공단 실시간 API 키가 올바르게 작동하고 있습니다. 실시간 대기 정보를 조회합니다.</div>
    </div>
    """
st.sidebar.markdown(api_status_html, unsafe_allow_html=True)

# 5. 데이터 필터링 실행
filtered_sources = []
for s in sources:
    # 1. 신뢰도 필터
    if s["satellite_metadata"]["confidence"] < min_conf:
        continue
    # 2. 산단 구역 필터
    if selected_region != "전체" and selected_region not in s["address"]:
        continue
    # 3. 배출원 타입 필터
    if selected_type != "전체" and s["source_type"] != selected_type:
        continue
    filtered_sources.append(s)

stations = db_manager.find("air_quality_stations")

# 6. 메인 헤더 레이아웃
st.markdown("<div class='main-title'>EcoMap AIR POLLUTION MONITOR</div>", unsafe_allow_html=True)
# 7. KPI 대시보드 카드 영역
summary = spatial_analyzer.get_dashboard_summary()

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>🛰️ 모니터링 배출원 수</div>
        <div class='metric-value'>{len(filtered_sources)} <span style='font-size: 15px; color: #aaa;'>개소</span></div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>🏫 연동 대기질 측정소</div>
        <div class='metric-value'>{len(stations)} <span style='font-size: 15px; color: #aaa;'>지점</span></div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    # 실시간 평균 대기오염지수(KHAI) 산출
    active_khai = []
    for st_doc in stations:
        log = db_manager.find_one("air_quality_logs", {"station_name": st_doc["station_name"]}, sort=[("data_time", -1)])
        if log:
            active_khai.append(log["khai"])
    avg_khai = int(sum(active_khai) / len(active_khai)) if active_khai else 0
    
    khai_color = "#3498db" if avg_khai <= 50 else "#2ecc71" if avg_khai <= 100 else "#e67e22" if avg_khai <= 250 else "#e74c3c"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>🌡️ 산업단지 평균 KHAI 지수</div>
        <div class='metric-value' style='color: {khai_color};'>{avg_khai} <span style='font-size: 15px; color: #aaa;'>단위</span></div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    # 초정밀 배출원 (신뢰도 90% 이상)
    high_alert = sum(1 for s in filtered_sources if s["satellite_metadata"]["confidence"] >= 0.9)
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>⚠️ 고신뢰도 배출원 특위</div>
        <div class='metric-value' style='color: #e74c3c;'>{high_alert} <span style='font-size: 15px; color: #aaa;'>개소</span></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 8. 메인 스플릿 레이아웃 (좌측: 인터랙티브 지도, 우측: 상세 데이터 융합 분석 패널)
layout_col1, layout_col2 = st.columns([1.7, 1.3])

# 분석 대상 배출원 선택 (사용자 상호작용성 강화)
source_options = [s["name"] for s in filtered_sources]
selected_source = None

with layout_col2:
    st.markdown("### 🔎 배출원 영향 다차원 분석")
    if source_options:
        selected_source = st.selectbox(
            "📍 상세 모니터링할 배출원 선택",
            source_options,
            help="선택 시, 해당 배출원을 기준으로 주변 측정소와의 거리 및 실시간 오염지수를 분석합니다."
        )
    else:
        st.warning("선택된 필터 조건에 부합하는 배출원이 없습니다. 필터를 조정해 주세요.")

# 실시간 분석 연산 수행
analysis_result = None
if selected_source:
    # 비동기 함수 동기식 처리로 Streamlit 연결 보장
    import asyncio
    analysis_result = asyncio.run(spatial_analyzer.analyze_source_impact(selected_source, radius_km))

with layout_col1:
    st.markdown("### 🗺️ 대기오염 공간 인터랙티브 맵")
    # Folium 지도 생성 및 Streamlit 렌더링
    map_interaction = render_pollution_map(
        sources=filtered_sources,
        stations=stations,
        analysis_data=analysis_result,
        selected_source_name=selected_source
    )

# 9. 우측 컬럼 - 상세 분석 패널 채우기
with layout_col2:
    if analysis_result:
        src_info = analysis_result["source_info"]
        metrics = analysis_result["summary_metrics"]
        
        # Glassmorphic Detail Panel
        st.markdown(f"""
        <div class='detail-panel'>
            <h3 style='margin: 0 0 10px 0; color: #e74c3c;'>🛰️ {src_info['name']}</h3>
            <p style='font-size: 13px; color: #bdc3c7;'>유형: <b>{TYPE_TRANSLATION.get(src_info['type'], src_info['type'])}</b> | 분석 위성: TROPOMI/Sentinel-5P</p>
            <table style='width: 100%; border-collapse: collapse; font-size: 13px; margin: 15px 0;'>
                <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'><td style='padding: 6px 0; color: #aaa;'>위성 관측 농도</td><td style='text-align: right; font-weight: bold; color: #f1c40f;'>{src_info['satellite_value']:.3e} mol/m²</td></tr>
                <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'><td style='padding: 6px 0; color: #aaa;'>탐지 인공지능 신뢰도</td><td style='text-align: right; font-weight: bold; color: #2ecc71;'>{src_info['confidence'] * 100:.1f}%</td></tr>
                <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'><td style='padding: 6px 0; color: #aaa;'>반경 {radius_km}km 내 측정소</td><td style='text-align: right; font-weight: bold;'>{metrics['monitored_stations_count']} 개소</td></tr>
                <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'><td style='padding: 6px 0; color: #aaa;'>인근 평균 미세먼지(PM10)</td><td style='text-align: right; font-weight: bold;'>{metrics['average_pm10']} ㎍/㎥</td></tr>
                <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'><td style='padding: 6px 0; color: #aaa;'>인근 평균 초미세먼지(PM2.5)</td><td style='text-align: right; font-weight: bold;'>{metrics['average_pm25']} ㎍/㎥</td></tr>
                <tr><td style='padding: 6px 0; color: #aaa;'>종합 대기 위해도 평가</td><td style='text-align: right; font-weight: bold; color: #e74c3c;'>{metrics['impact_risk_rating']}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        # 인근 측정소 거리 테이블 표시
        if analysis_result["nearby_stations"]:
            st.markdown("##### 🏫 반경 내 연동 측정소 대기질 상세")
            st.dataframe(
                analysis_result["nearby_stations"],
                column_config={
                    "station_name": "측정소명",
                    "distance_km": "이격 거리 (km)",
                    "khai": "KHAI 지수",
                    "khai_grade": "등급",
                    "pm10": "PM10 (㎍/㎥)",
                    "pm25": "PM2.5 (㎍/㎥)",
                    "measured_at": "측정 시각"
                },
                hide_index=True
            )
        else:
            st.warning(f"설정된 반경 {radius_km}km 이내에 위치한 대기질 측정소가 존재하지 않습니다.")

st.markdown("<br><hr><br>", unsafe_allow_html=True)

# 10. 통계 분석 대시보드 하단 레이아웃 (차트류 렌더링)
st.markdown("### 📊 다차원 대기오염 통계 및 분석 리포트")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # 배출원 종류 도넛 차트
    render_source_type_pie(summary["source_type_distribution"])

with chart_col2:
    if analysis_result and analysis_result["nearby_stations"]:
        # 거리 vs 대기질 상관 산점도
        render_distance_pollution_scatter(analysis_result["nearby_stations"])
    else:
        st.info("지도의 배출원을 선택하시면 이격 거리별 오염 상관 산점도가 활성화됩니다.")

# 전체 측정 물질 비교 막대 차트 (가장 하단 전체 너비로 시각화)
if analysis_result and analysis_result["nearby_stations"]:
    st.markdown("<br>", unsafe_allow_html=True)
    render_pollutant_multi_bar(analysis_result["nearby_stations"])
