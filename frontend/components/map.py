import datetime
import folium
from folium.plugins import MiniMap
import streamlit as st
from streamlit_folium import st_folium

# KHAI 등급별 테마 칼라 정의
COLOR_PALETTE = {
    "좋음": "#3498db",      # 시원한 파랑
    "보통": "#2ecc71",      # 싱그러운 초록
    "나쁨": "#e67e22",      # 경고용 주황
    "매우나쁨": "#e74c3c",    # 위험한 빨강
    "정보없음": "#95a5a6"     # 차분한 회색
}

# 배출원 타입 한글 번역 매핑
TYPE_TRANSLATION = {
    "stack": "산업용 굴뚝 (Smokestack)",
    "factory_roof": "공장 지붕 배출 (Roof)",
    "waste_treatment": "폐기물 처리 구역",
    "agricultural": "농축산 유기물 지역",
    "satellite_area": "위성 분석 구역 (Satellite Area)",
    "unknown": "일반 오염 유발 시설"
}

def render_pollution_map(sources, stations, analysis_data=None, selected_source_name=None):
    """Folium 인터랙티브 지도를 생성하고 렌더링을 제어합니다."""
    
    # 1. 초기 맵 중심 설정 (선택된 배출원이 있으면 해당 위치로, 없으면 시화반월단지 중심)
    map_center = [37.31, 126.76]
    zoom_level = 11
    
    if selected_source_name and analysis_data:
        coords = analysis_data["source_info"]["coordinates"]
        # GeoJSON은 [lon, lat]이므로 folium용 [lat, lon]으로 뒤집음
        map_center = [coords[1], coords[0]]
        zoom_level = 13

    # Premium Dark Mode 구현을 위해 CartoDB Dark Matter 타일 사용!
    m = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles="CartoDB dark_matter",
        control_scale=True
    )
    
    # 미니맵 플러그인 추가 (고급스러운 룩앤필 완성)
    MiniMap(toggle_display=True, position="bottomright", width=120, height=120).add_to(m)

    # 2. 오염 배출원 레이어 적재
    fg_sources = folium.FeatureGroup(name="🛰️ 위성 배출원 (Point/Polygon)")
    
    for src in sources:
        src_name = src["name"]
        loc = src["location"]
        src_type = TYPE_TRANSLATION.get(src["source_type"], src["source_type"])
        metadata = src["satellite_metadata"]
        
        # 탐지 신뢰도와 관측 밀도를 바탕으로 원의 반지름 및 컬러 계산
        val = metadata["observation_value"]
        conf = metadata["confidence"]
        
        # 반경 계산식 (관측 수치에 비례)
        marker_radius = max(8, min(25, int(val * 1.5e5)))
        # 신뢰도에 따른 배출원 불투명도 조절 (높을수록 진함)
        fill_opacity = max(0.4, min(0.9, conf))
        
        # 선택된 배출원 강조 효과 (테두리 두께 및 색상 변경)
        is_selected = (src_name == selected_source_name)
        border_color = "#f1c40f" if is_selected else "#e74c3c"
        border_weight = 4 if is_selected else 1.5

        # 팝업 HTML 템플릿 생성 (Glassmorphism 분위기의 세련된 테마)
        popup_html = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif; width: 280px; padding: 5px; color: #2c3e50;">
            <h4 style="margin: 0 0 8px 0; color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 5px;">🔥 {src_name}</h4>
            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">분류</td><td>{src_type}</td></tr>
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">관측 밴드</td><td>{metadata['band_type']}</td></tr>
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">위성 분석 농도</td><td>{val:.2e} mol/m²</td></tr>
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">AI 탐지 신뢰도</td><td>{conf * 100:.1f}%</td></tr>
                <tr><td style="font-weight: bold; padding: 4px 0;">분석 위성</td><td>{metadata['satellite_name']}</td></tr>
            </table>
            <div style="margin-top: 8px; font-size: 10px; color: #7f8c8d; text-align: right;">*AIHub 위성 초분광 대기질 데이터 기반</div>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=300)

        # Point 형태 렌더링
        if loc["type"] == "Point":
            lon, lat = loc["coordinates"]
            # CircleMarker로 발광 구체 구현
            folium.CircleMarker(
                location=[lat, lon],
                radius=marker_radius,
                popup=popup,
                color=border_color,
                weight=border_weight,
                fill=True,
                fill_color="#e74c3c",
                fill_opacity=fill_opacity,
                tooltip=f"<b>{src_name}</b> (클릭하여 상세 조회)",
            ).add_to(fg_sources)
            
        # Polygon 형태 렌더링 (산업 단지 및 위성 영역)
        elif loc["type"] == "Polygon":
            coords = loc["coordinates"][0]
            # GeoJSON은 [경도, 위도]이므로 [위도, 경도]로 포맷 체인지
            poly_coords = [[pt[1], pt[0]] for pt in coords]
            
            # 위성 분석 영역의 경우 스페셜 프리미엄 네온 스타일링 적용!
            if src["source_type"] == "satellite_area":
                poly_fill_color = "#00f2fe"
                poly_border_color = "#f1c40f" if is_selected else "#4facfe"
                poly_weight = border_weight + 1 if is_selected else 2.5
                poly_tooltip = f"🛰️ <b>{src_name} (위성 분석 영역)</b>"
            else:
                poly_fill_color = "#e67e22"
                poly_border_color = border_color
                poly_weight = border_weight
                poly_tooltip = f"🏢 <b>{src_name} (영역)</b>"
            
            folium.Polygon(
                locations=poly_coords,
                popup=popup,
                color=poly_border_color,
                weight=poly_weight,
                fill=True,
                fill_color=poly_fill_color,
                fill_opacity=fill_opacity * 0.6 if src["source_type"] == "satellite_area" else fill_opacity * 0.7,
                tooltip=poly_tooltip,
            ).add_to(fg_sources)

    # 3. 실시간 대기질 측정소 레이어 적재
    fg_stations = folium.FeatureGroup(name="🏫 실시간 대기질 측정소 (AirKorea)")
    
    for st_doc in stations:
        st_name = st_doc["station_name"]
        lon, lat = st_doc["location"]["coordinates"]
        
        # 측정소의 최신 대기질 로그 확인
        from backend.database import db_manager
        latest_log = db_manager.find_one(
            "air_quality_logs",
            {"station_name": st_name},
            sort=[("data_time", -1)]
        )
        
        # 기본 정보 설정
        pm10, pm25, khai = "-", "-", "-"
        grade = "정보없음"
        update_time = "측정대기"
        
        if latest_log:
            pm10 = f"{latest_log['pm10']} ㎍/㎥"
            pm25 = f"{latest_log['pm25']} ㎍/㎥"
            khai = latest_log["khai"]
            grade = latest_log.get("khai_grade", "정보없음")
            # 한국 표준 시간 변환 표시 (JSON 로드 시 문자열 형태로 복원될 경우 대응)
            local_time = latest_log["data_time"]
            if isinstance(local_time, str):
                try:
                    # ISO 포맷("2026-06-08T00:00:00") 및 일반 포맷("2026-06-08 00:00:00") 파싱
                    if "T" in local_time:
                        local_time = datetime.datetime.fromisoformat(local_time.replace("Z", ""))
                    else:
                        local_time = datetime.datetime.strptime(local_time, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        local_time = datetime.datetime.strptime(local_time, "%Y-%m-%d %H:%M")
                    except Exception:
                        pass
            
            if hasattr(local_time, "strftime"):
                update_time = local_time.strftime("%Y-%m-%d %H:%M")
            else:
                update_time = str(local_time)

        grade_color = COLOR_PALETTE.get(grade, "#95a5a6")

        station_html = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif; width: 220px; padding: 5px;">
            <h4 style="margin: 0 0 8px 0; color: {grade_color}; border-bottom: 2px solid {grade_color}; padding-bottom: 5px;">🏫 {st_name} 측정소</h4>
            <div style="font-size: 20px; font-weight: bold; text-align: center; margin: 10px 0; color: #2c3e50;">
                통합대기: <span style="color: {grade_color}">{khai} ({grade})</span>
            </div>
            <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">미세먼지(PM10)</td><td style="text-align: right;">{pm10}</td></tr>
                <tr style="border-bottom: 1px solid #eee;"><td style="font-weight: bold; padding: 4px 0;">초미세먼지(PM2.5)</td><td style="text-align: right;">{pm25}</td></tr>
                <tr><td style="font-weight: bold; padding: 4px 0;">측정 시각</td><td style="text-align: right; color: #7f8c8d;">{update_time}</td></tr>
            </table>
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(station_html, max_width=250),
            icon=folium.Icon(color="cadetblue" if grade == "좋음" else "lightgreen" if grade == "보통" else "orange" if grade == "나쁨" else "red", icon="info-sign"),
            tooltip=f"🏫 <b>{st_name} 측정소</b> (상태: <span style='color:{grade_color}'>{grade}</span>)",
        ).add_to(fg_stations)

    # 4. 공간 분석 데이터 기반의 연결 가시화 (원 & 연결 점선 그리기)
    if selected_source_name and analysis_data:
        coords = analysis_data["source_info"]["coordinates"]
        s_lon, s_lat = coords[0], coords[1]
        rad_km = analysis_data["radius_km"]
        
        # 반경 가이드라인 그리기 (점선 반경 서클)
        folium.Circle(
            location=[s_lat, s_lon],
            radius=rad_km * 1000.0,
            color="#3498db",
            weight=1.5,
            fill=True,
            fill_color="#3498db",
            fill_opacity=0.06,
            dash_array="5, 8",
            tooltip=f"배출원 영향 분석 반경: {rad_km}km"
        ).add_to(m)

        # 근처 측정소까지 연결하는 점선 그리기
        for st_near in analysis_data["nearby_stations"]:
            # 측정소 좌표를 가져오기 위해 stations 목록에서 매칭
            st_name = st_near["station_name"]
            st_doc = next((s for s in stations if s["station_name"] == st_name), None)
            
            if st_doc:
                st_lon, st_lat = st_doc["location"]["coordinates"]
                dist_km = st_near["distance_km"]
                grade = st_near["khai_grade"]
                grade_color = COLOR_PALETTE.get(grade, "#7a7a7a")
                
                # 거리선 그리기
                folium.PolyLine(
                    locations=[[s_lat, s_lon], [st_lat, st_lon]],
                    color=grade_color,
                    weight=2,
                    opacity=0.7,
                    dash_array="4, 6",
                    tooltip=f"{selected_source_name} ↔ {st_name} (거리: {dist_km}km)"
                ).add_to(m)

    # 레이어들 지도에 통합
    fg_sources.add_to(m)
    fg_stations.add_to(m)
    folium.LayerControl().add_to(m)
    
    # 5. Streamlit Folium 컴포넌트를 이용해 렌더링 호출
    # dark mode에 어울리도록 width 100% 설정
    return st_folium(m, width=700, height=520, returned_objects=["last_active_drawing"])
