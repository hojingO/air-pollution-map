import logging
from bson import ObjectId
from backend.database import db_manager
from backend.services.airkorea import airkorea_client

logger = logging.getLogger("Analyzer-Service")

def get_centroid(location_geojson: dict):
    """GeoJSON Point 또는 Polygon으로부터 대표 중심좌표 [경도, 위도]를 산출합니다."""
    geom_type = location_geojson.get("type")
    coords = location_geojson.get("coordinates")
    
    if geom_type == "Point":
        return coords[0], coords[1]
    
    elif geom_type == "Polygon":
        # 단일 다각형 링 구조 가정 (첫 번째 리스트)
        outer_ring = coords[0]
        # 닫힌 도형의 마지막 중복점 제외
        points = outer_ring[:-1] if outer_ring[0] == outer_ring[-1] else outer_ring
        
        sum_lon = sum(p[0] for p in points)
        sum_lat = sum(p[1] for p in points)
        count = len(points)
        
        return sum_lon / count, sum_lat / count
        
    return 0.0, 0.0

class SpatialAnalyzer:
    async def analyze_source_impact(self, source_name: str, radius_km: float = 8.0):
        """특정 배출원 주위 반경 내의 측정소를 검색하고, 실시간 대기질 수치와 융합 분석합니다."""
        # 1. 배출원 정보 조회
        source = db_manager.find_one("pollution_sources", {"name": source_name})
        if not source:
            logger.warning(f"❌ [Analyzer] 배출원을 찾을 수 없습니다: {source_name}")
            return None
            
        # 2. 중심 좌표 추출
        lon, lat = get_centroid(source["location"])
        
        # 3. 반경 내 최단 거리 측정소 조회 (미터 단위 변환)
        radius_meters = radius_km * 1000.0
        nearest_stations = db_manager.get_nearest_stations(lon, lat, max_distance_meters=radius_meters, limit=5)
        
        stations_analysis = []
        total_pm10 = 0.0
        total_pm25 = 0.0
        total_khai = 0
        valid_station_count = 0
        
        # 4. 각 측정소별 실시간 대기질 데이터 연동 및 가공
        for item in nearest_stations:
            station = item["station"]
            distance = item["distance"]
            st_name = station["station_name"]
            
            # 실시간 대기질 대입 (API 호출 또는 simulated 폴백)
            aqi_log = await airkorea_client.get_realtime_air_quality(st_name)
            
            if aqi_log:
                stations_analysis.append({
                    "station_name": st_name,
                    "distance_km": round(distance / 1000.0, 2),
                    "pm10": aqi_log["pm10"],
                    "pm25": aqi_log["pm25"],
                    "o3": aqi_log["o3"],
                    "no2": aqi_log["no2"],
                    "so2": aqi_log["so2"],
                    "khai": aqi_log["khai"],
                    "khai_grade": aqi_log["khai_grade"],
                    "measured_at": aqi_log["data_time"]
                })
                
                total_pm10 += aqi_log["pm10"]
                total_pm25 += aqi_log["pm25"]
                total_khai += aqi_log["khai"]
                valid_station_count += 1
                
        # 5. 종합 영향 평가 지표 산출
        avg_pm10 = round(total_pm10 / valid_station_count, 1) if valid_station_count > 0 else 0.0
        avg_pm25 = round(total_pm25 / valid_station_count, 1) if valid_station_count > 0 else 0.0
        avg_khai = int(total_khai / valid_station_count) if valid_station_count > 0 else 0
        
        # 종합 위해성 분석 등급
        if avg_khai <= 50:
            impact_risk = "안전 (Low Risk)"
        elif avg_khai <= 100:
            impact_risk = "주의 (Moderate)"
        elif avg_khai <= 150:
            impact_risk = "영향 있음 (Unhealthy for Sensitive Groups)"
        else:
            impact_risk = "위험 (High Risk)"
            
        return {
            "source_info": {
                "name": source["name"],
                "type": source["source_type"],
                "coordinates": [lon, lat],
                "satellite_value": source["satellite_metadata"]["observation_value"],
                "confidence": source["satellite_metadata"]["confidence"]
            },
            "radius_km": radius_km,
            "nearby_stations": stations_analysis,
            "summary_metrics": {
                "average_pm10": avg_pm10,
                "average_pm25": avg_pm25,
                "average_khai": avg_khai,
                "impact_risk_rating": impact_risk,
                "monitored_stations_count": valid_station_count
            }
        }

    def get_dashboard_summary(self):
        """대시보드 통계용 메인 종합 지표를 집계합니다."""
        sources = db_manager.find("pollution_sources")
        stations = db_manager.find("air_quality_stations")
        
        # 1. 배출원 종류별 수량 파악
        source_types = {}
        for s in sources:
            t = s.get("source_type", "unknown")
            source_types[t] = source_types.get(t, 0) + 1
            
        # 2. 실시간 측정소별 최신 KHAI 등급 분포 파악
        grade_distribution = {"좋음": 0, "보통": 0, "나쁨": 0, "매우나쁨": 0, "정보없음": 0}
        
        for st in stations:
            st_name = st["station_name"]
            # DB 캐시나 메모리에서 최신값 1건 추출
            latest_log = db_manager.find_one(
                "air_quality_logs",
                {"station_name": st_name},
                sort=[("data_time", -1)]
            )
            if latest_log:
                grade = latest_log.get("khai_grade", "정보없음")
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
            else:
                grade_distribution["정보없음"] += 1
                
        return {
            "total_sources_count": len(sources),
            "total_stations_count": len(stations),
            "source_type_distribution": source_types,
            "air_quality_grade_distribution": grade_distribution
        }

spatial_analyzer = SpatialAnalyzer()
