import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

# Premium Dark Mode 테마 레이아웃 프리셋
DARK_THEME_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font_color": "#e0e0e0",
    "title_font_size": 16,
    "title_font_family": "Outfit, Malgun Gothic, sans-serif",
    "xaxis": {"gridcolor": "rgba(255,255,255,0.08)", "tickfont": {"size": 10}},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.08)", "tickfont": {"size": 10}},
    "margin": {"t": 40, "b": 30, "l": 40, "r": 20}
}

# 배출원 타입 매핑
TYPE_KOREAN = {
    "stack": "산업용 굴뚝",
    "factory_roof": "공장 지붕",
    "waste_treatment": "폐기물 처리",
    "agricultural": "농축산 지역",
    "unknown": "일반 대기 시설"
}

def render_source_type_pie(type_distribution):
    """배출원 분류별 분포를 미려한 도넛 차트로 렌더링합니다."""
    if not type_distribution:
        st.info("시각화할 배출원 분류 통계 데이터가 부족합니다.")
        return
        
    labels = [TYPE_KOREAN.get(k, k) for k in type_distribution.keys()]
    values = list(type_distribution.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.55,
        marker=dict(colors=["#e74c3c", "#e67e22", "#9b59b6", "#34495e", "#1abc9c"]),
        textinfo="percent+value",
        insidetextorientation="radial"
    )])
    
    fig.update_layout(
        title="🛰️ 위성 관측 배출원 종류 분포",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        **DARK_THEME_LAYOUT
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_distance_pollution_scatter(nearby_stations):
    """배출원 중심으로부터의 거리(km)와 대기오염지수(KHAI)의 상관산점도를 렌더링합니다."""
    if not nearby_stations:
        st.info("선택된 반경 내에 작동 중인 측정소가 없습니다. 분석 범위를 넓혀보세요.")
        return
        
    df = pd.DataFrame(nearby_stations)
    
    # 산점도 핀 생성
    fig = px.scatter(
        df,
        x="distance_km",
        y="khai",
        size="pm10",
        color="khai_grade",
        hover_name="station_name",
        labels={"distance_km": "배출원과의 거리 (km)", "khai": "실시간 통합대기환경지수 (KHAI)"},
        color_discrete_map={
            "좋음": "#3498db",
            "보통": "#2ecc71",
            "나쁨": "#e67e22",
            "매우나쁨": "#e74c3c"
        },
        category_orders={"khai_grade": ["좋음", "보통", "나쁨", "매우나쁨"]}
    )
    
    # 트렌드선 또는 선형 관계 가이드 직접 계산 및 렌더링 (경향성 파악)
    if len(df) > 1:
        df_sorted = df.sort_values(by="distance_km")
        fig.add_trace(go.Scatter(
            x=df_sorted["distance_km"],
            y=df_sorted["khai"],
            mode="lines",
            name="거리별 추세 경향",
            line=dict(color="rgba(255, 255, 255, 0.4)", width=1.5, dash="dash"),
            showlegend=True
        ))
        
    fig.update_traces(
        marker=dict(line=dict(width=1, color="white")),
        selector=dict(mode="markers")
    )
    
    fig.update_layout(
        title="📏 배출원 이격 거리별 실시간 대기환경지수(KHAI) 상관도",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        **DARK_THEME_LAYOUT
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_pollutant_multi_bar(nearby_stations):
    """측정소별 다양한 대기오염 핵심 물질 농도를 비교하는 다중 컬럼 차트"""
    if not nearby_stations:
        return
        
    df = pd.DataFrame(nearby_stations)
    
    # 시각화할 컬럼 필터
    fig = go.Figure()
    
    # PM10 막대 추가 (1차 Y축)
    fig.add_trace(go.Bar(
        x=df["station_name"],
        y=df["pm10"],
        name="미세먼지(PM10) [㎍/㎥]",
        marker_color="#1abc9c",
        offsetgroup=1
    ))
    
    # PM2.5 막대 추가 (1차 Y축)
    fig.add_trace(go.Bar(
        x=df["station_name"],
        y=df["pm25"],
        name="초미세먼지(PM2.5) [㎍/㎥]",
        marker_color="#9b59b6",
        offsetgroup=2
    ))

    # NO2 오염 농도 선 추가 (2차 Y축으로 미량 물질 매핑)
    fig.add_trace(go.Scatter(
        x=df["station_name"],
        y=df["no2"] * 1000, # 가시성을 위해 단위를 ppb 등으로 변환 표시
        name="이산화질소(NO2) [x10⁻³ ppm]",
        line=dict(color="#f1c40f", width=3),
        yaxis="y2",
    ))
    
    # DARK_THEME_LAYOUT 복사 및 yaxis 속성 병합
    layout_args = DARK_THEME_LAYOUT.copy()
    layout_args["yaxis"] = {
        **layout_args.get("yaxis", {}),
        "title": "먼지 농도 (㎍/㎥)"
    }
    layout_args["yaxis2"] = {
        "title": "NO2 농도 지수",
        "overlaying": "y",
        "side": "right"
    }

    fig.update_layout(
        title="🧪 반경 내 측정소별 미세먼지 및 가스성 물질 상세 농도 비교",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        **layout_args
    )
    
    st.plotly_chart(fig, use_container_width=True)
