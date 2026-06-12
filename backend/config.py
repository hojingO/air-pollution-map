import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)

class Settings:
    PROJECT_NAME: str = "대기오염 배출원 지도 서비스 (EcoMap)"
    
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/air_pollution")
    DB_NAME: str = "air_pollution"
    
    # FastAPI settings
    HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("FASTAPI_PORT", 8000))
    
    # AirKorea API settings
    AIRKOREA_SERVICE_KEY: str = os.getenv("AIRKOREA_SERVICE_KEY", "")
    
    # API endpoints
    AIRKOREA_STATION_URL: str = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
    AIRKOREA_AQI_URL: str = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"

settings = Settings()
