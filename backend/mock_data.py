import datetime
import random
import math
from backend.database import db_manager

# 대한민국 주요 산업단지 및 대기오염 배출원 정보 정의 (좌표계: 경도/위도)
INDUSTRIAL_REGIONS = {
    "시화반월단지": {
        "center": [126.76, 37.31],
        "stations": [
            {"name": "정왕동", "coords": [126.7244, 37.3233], "addr": "경기 시흥시 정왕대로 233번길 19"},
            {"name": "원시동", "coords": [126.7845, 37.3045], "addr": "경기 안산시 단원구 산단로 12"},
            {"name": "고잔동", "coords": [126.8123, 37.3182], "addr": "경기 안산시 단원구 적금로 1"}
        ],
        "sources": [
            {"name": "시화공단 도금공장 A", "type": "factory_roof", "offset": [-0.015, 0.008], "conf": 0.94, "val": 4.8e-5, "gas": "SO2"},
            {"name": "시화공단 화학공장 B", "type": "stack", "offset": [-0.005, -0.012], "conf": 0.88, "val": 5.2e-5, "gas": "NO2"},
            {"name": "반월공단 제철소 C", "type": "stack", "offset": [0.024, -0.008], "conf": 0.97, "val": 8.5e-5, "gas": "CO"},
            {"name": "반월공단 섬유공장 D", "type": "factory_roof", "offset": [0.012, 0.018], "conf": 0.79, "val": 3.1e-5, "gas": "NO2"},
            {"name": "시흥 폐기물 처리장 E", "type": "waste_treatment", "offset": [-0.028, -0.022], "conf": 0.91, "val": 6.9e-5, "gas": "H2S"}
        ]
    },
    "울산석유화학단지": {
        "center": [129.36, 35.51],
        "stations": [
            {"name": "여천동(울산)", "coords": [129.3622, 35.5255], "addr": "울산 남구 여천로 38"},
            {"name": "온산읍", "coords": [129.3522, 35.4388], "addr": "울산 울주군 온산읍 덕신로 242"},
            {"name": "신정동", "coords": [129.3144, 35.5399], "addr": "울산 남구 돋질로 97"}
        ],
        "sources": [
            {"name": "울산 정유공장 A", "type": "stack", "offset": [0.008, 0.012], "conf": 0.99, "val": 1.2e-4, "gas": "SO2"},
            {"name": "울산 석유화학공장 B", "type": "stack", "offset": [-0.012, -0.008], "conf": 0.95, "val": 9.8e-5, "gas": "NO2"},
            {"name": "온산 제련소 C", "type": "stack", "offset": [-0.008, -0.065], "conf": 0.96, "val": 1.1e-4, "gas": "SO2"},
            {"name": "남구 자동차 조립공장 D", "type": "factory_roof", "offset": [-0.035, 0.025], "conf": 0.84, "val": 4.0e-5, "gas": "CO"},
            {"name": "울산 석유공사 정유 기지 E", "type": "factory_roof", "offset": [0.015, -0.015], "conf": 0.89, "val": 5.5e-5, "gas": "VOCs"}
        ]
    },
    "여수국가산단": {
        "center": [127.70, 34.82],
        "stations": [
            {"name": "여천동", "coords": [127.6922, 34.8021], "addr": "전남 여수시 쌍봉로 57"},
            {"name": "삼일동", "coords": [127.7288, 34.8366], "addr": "전남 여수시 여수산단로 100"}
        ],
        "sources": [
            {"name": "여수 석유화학 A", "type": "stack", "offset": [0.012, 0.015], "conf": 0.98, "val": 1.5e-4, "gas": "NO2"},
            {"name": "여수 기초소재 B", "type": "stack", "offset": [-0.015, 0.005], "conf": 0.92, "val": 8.4e-5, "gas": "SO2"},
            {"name": "여수 화력발전소 C", "type": "stack", "offset": [0.028, 0.022], "conf": 0.99, "val": 2.1e-4, "gas": "NO2"},
            {"name": "여수 포장재 플랜트 D", "type": "factory_roof", "offset": [-0.008, -0.018], "conf": 0.76, "val": 2.9e-5, "gas": "CO"}
        ]
    },
    "대산석유화학단지": {
        "center": [126.35, 37.00],
        "stations": [
            {"name": "독곶리", "coords": [126.3755, 37.0122], "addr": "충남 서산시 대산읍 독곶1로 50"},
            {"name": "동문동", "coords": [126.4633, 36.7822], "addr": "충남 서산시 번화로 19"}
        ],
        "sources": [
            {"name": "대산 정유공장 A", "type": "stack", "offset": [0.005, 0.006], "conf": 0.97, "val": 1.05e-4, "gas": "SO2"},
            {"name": "대산 화학 플랜트 B", "type": "stack", "offset": [-0.012, -0.005], "conf": 0.91, "val": 7.8e-5, "gas": "NO2"},
            {"name": "대산 고분자 수지 공장 C", "type": "factory_roof", "offset": [0.018, -0.012], "conf": 0.85, "val": 4.6e-5, "gas": "VOCs"}
        ]
    },
    "광양국가산단": {
        "center": [127.69, 34.91],
        "stations": [
            {"name": "태인동", "coords": [127.7655, 34.9355], "addr": "전남 광양시 태인길 20"},
            {"name": "중동", "coords": [127.6988, 34.9422], "addr": "전남 광양시 시청로 30"}
        ],
        "sources": [
            {"name": "광양 제철소 고로 1", "type": "stack", "offset": [0.065, -0.025], "conf": 0.99, "val": 2.4e-4, "gas": "CO"},
            {"name": "광양 제철소 고로 2", "type": "stack", "offset": [0.071, -0.021], "conf": 0.99, "val": 2.2e-4, "gas": "CO"},
            {"name": "광양 제철 배후단지 공장 A", "type": "factory_roof", "offset": [0.012, 0.008], "conf": 0.87, "val": 5.1e-5, "gas": "NO2"},
            {"name": "광양 액화가스 기지 B", "type": "factory_roof", "offset": [0.045, -0.045], "conf": 0.82, "val": 3.5e-5, "gas": "VOCs"}
        ]
    }
}

def generate_polygon_coordinates(center_lon, center_lat, size=0.003):
    """지정된 중심좌표 주위에 정오각형 다각형 GeoJSON 좌표를 생성합니다."""
    coords = []
    for i in range(5):
        angle = i * (2.0 * 3.141592 / 5)
        offset_lon = size * 1.2 * math.cos(angle)
        offset_lat = size * math.sin(angle)
        coords.append([center_lon + offset_lon, center_lat + offset_lat])
    # 첫 좌표와 끝 좌표가 일치해야 Polygon 검증 성공
    coords.append(coords[0])
    return [coords]

def initialize_mock_data():
    """배출원(GeoJSON Point/Polygon) 및 대기질 측정소 기초 데이터를 적재합니다."""
    # 1. 기존 데이터 초기화
    db_manager.delete_many("pollution_sources")
    db_manager.delete_many("air_quality_stations")
    db_manager.delete_many("air_quality_logs")
    
    stations_to_insert = []
    sources_to_insert = []
    
    # 2. 산업단지 순회하며 데이터 맵핑
    for region_name, region in INDUSTRIAL_REGIONS.items():
        # 측정소 데이터 준비
        for st in region["stations"]:
            stations_to_insert.append({
                "station_name": st["name"],
                "location": {
                    "type": "Point",
                    "coordinates": st["coords"]
                },
                "addr": st["addr"],
                "oper": "한국환경공단",
                "created_at": datetime.datetime.utcnow()
            })
        
        # 배출원 데이터 준비
        center_lon, center_lat = region["center"]
        for idx, src in enumerate(region["sources"]):
            lon = center_lon + src["offset"][0]
            lat = center_lat + src["offset"][1]
            
            # 홀수 인덱스 소스는 면적(Polygon), 짝수 인덱스 소스는 좌표점(Point)으로 다각화 구현!
            if idx % 2 == 1:
                loc_type = "Polygon"
                coordinates = generate_polygon_coordinates(lon, lat)
            else:
                loc_type = "Point"
                coordinates = [lon, lat]
                
            sources_to_insert.append({
                "name": src["name"],
                "source_type": src["type"],
                "location": {
                    "type": loc_type,
                    "coordinates": coordinates
                },
                "address": f"대한민국 주요 산업지역 ({region_name} 산단 내)",
                "satellite_metadata": {
                    "satellite_name": "TROPOMI / Sentinel-5P",
                    "band_type": f"{src['gas']} Column Density",
                    "pixel_resolution": "3.5km x 5.5km",
                    "observation_value": src["val"],
                    "confidence": src["conf"]
                },
                "created_at": datetime.datetime.utcnow()
            })
            
    # DB에 적재
    db_manager.insert_many("air_quality_stations", stations_to_insert)
    db_manager.insert_many("pollution_sources", sources_to_insert)
    
    # 3. 실시간 대기질 초기 로그 생성 (측정소마다 24시간 동안의 모의 이력 데이터 생성)
    logs_to_insert = []
    now = datetime.datetime.utcnow()
    
    for st in stations_to_insert:
        st_name = st["station_name"]
        
        # 시간별 변화가 생기도록 24시간 데이터 시뮬레이션
        for h in range(24):
            time_delta = datetime.timedelta(hours=h)
            measurement_time = now - time_delta
            
            # 공해 지역별로 상이한 기본 오염도 및 시간대별 변동폭 시뮬레이션
            base_pm10 = 35 + random.uniform(5, 45)
            # 출퇴근 시간대 변동성 추가
            hour_factor = math.sin((measurement_time.hour - 8) * 3.14 / 6) * 15
            
            pm10 = max(10.0, round(base_pm10 + hour_factor, 1))
            pm25 = max(5.0, round(pm10 * 0.6 + random.uniform(-3, 3), 1))
            o3 = max(0.002, round(0.03 + 0.015 * math.sin(measurement_time.hour * 3.14 / 12), 3))
            no2 = max(0.005, round(0.02 + 0.01 * math.cos(measurement_time.hour * 3.14 / 12), 3))
            co = max(0.1, round(0.4 + random.uniform(-0.1, 0.2), 1))
            so2 = max(0.001, round(0.004 + random.uniform(-0.001, 0.003), 3))
            
            # KHAI 통합대기환경지수 간단히 계산
            khai = int(max(pm10, pm25 * 2.0, o3 * 1000))
            if khai <= 50:
                khai_grade = "좋음"
            elif khai <= 100:
                khai_grade = "보통"
            elif khai <= 250:
                khai_grade = "나쁨"
            else:
                khai_grade = "매우나쁨"
                
            logs_to_insert.append({
                "station_name": st_name,
                "data_time": measurement_time,
                "pm10": pm10,
                "pm25": pm25,
                "o3": o3,
                "no2": no2,
                "co": co,
                "so2": so2,
                "khai": khai,
                "khai_grade": khai_grade,
                "created_at": now
            })
            
    db_manager.insert_many("air_quality_logs", logs_to_insert)
    print(f"📊 [Mock Data] 적재 완료: 측정소 {len(stations_to_insert)}개, 배출원 {len(sources_to_insert)}개, 대기질 이력 {len(logs_to_insert)}건.")
    return len(sources_to_insert)

if __name__ == "__main__":
    initialize_mock_data()
