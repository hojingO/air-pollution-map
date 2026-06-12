from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import db_manager
from backend.mock_data import initialize_mock_data
from backend.services.analyzer import spatial_analyzer
from backend.services.airkorea import airkorea_client

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AIHub 위성 배출원 데이터와 에어코리아 실시간 대기질 정보를 융합한 분석 백엔드 API",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연결 보장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "database_mode": "Fallback (JSON File)" if db_manager.is_fallback else "MongoDB Atlas / Local",
        "endpoints": {
            "swagger_docs": "/docs",
            "sources": "/api/sources",
            "stations": "/api/stations",
            "dashboard_summary": "/api/summary"
        }
    }

@app.get("/api/status")
def get_db_status():
    """데이터베이스 연결 및 환경 설정 상태를 점검합니다."""
    return {
        "project_name": settings.PROJECT_NAME,
        "mongodb_connected": not db_manager.is_fallback,
        "database_type": "Smart Fallback JSON DB" if db_manager.is_fallback else "MongoDB Native",
        "airkorea_api_key_status": "Registered (Active)" if airkorea_client.is_configured else "Unregistered (Fallback Simulator Active)",
    }

@app.post("/api/init", status_code=201)
def seed_database():
    """모의 배출원 및 실측 측정소 기초 데이터를 데이터베이스에 초기 적재합니다."""
    try:
        inserted_count = initialize_mock_data()
        return {
            "status": "success",
            "message": f"성공적으로 {inserted_count}개의 고밀도 오염 배출원 및 측정소 데이터를 구축 완료했습니다.",
            "mode": "Fallback DB" if db_manager.is_fallback else "MongoDB Native"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 초기화 중 치명적인 에러 발생: {str(e)}")

@app.get("/api/sources")
def get_sources(
    source_type: str = Query(None, description="배출원 타입 필터 (stack, factory_roof, waste_treatment, etc.)"),
    min_confidence: float = Query(0.0, description="위성 탐지 최소 신뢰도 임계값 (0.0 ~ 1.0)"),
):
    """지정된 필터 조건에 부합하는 모든 대기오염 배출원 목록을 반환합니다."""
    query = {}
    if source_type:
        query["source_type"] = source_type
    if min_confidence > 0.0:
        query["satellite_metadata.confidence"] = {"$gte": min_confidence}
        
    try:
        # BSON ObjectId 포맷을 문자열로 전처리하여 JSON 직렬화 에러 예방
        sources = db_manager.find("pollution_sources", query)
        for s in sources:
            if "_id" in s:
                s["_id"] = str(s["_id"])
        return sources
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stations")
def get_stations():
    """등록된 전국 대기질 실측 측정소 목록을 조회합니다."""
    try:
        stations = db_manager.find("air_quality_stations")
        for s in stations:
            if "_id" in s:
                s["_id"] = str(s["_id"])
        return stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/{name}/analysis")
async def get_source_influence_analysis(
    name: str,
    radius_km: float = Query(5.0, description="영향 평가 분석 반경 범위 (단위: km, 기본값: 5km)")
):
    """특정 배출원 이름 기준, 주변 측정소들의 실시간 실측치 융합 분석 결과를 도출합니다."""
    analysis = await spatial_analyzer.analyze_source_impact(name, radius_km)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"배출원 '{name}'을(를) 시스템에서 찾을 수 없습니다.")
    return analysis

@app.get("/api/summary")
def get_dashboard_summary_stats():
    """Streamlit 메인 대시보드 및 지표 요약을 위한 통계 집계 결과를 가져옵니다."""
    try:
        return spatial_analyzer.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
