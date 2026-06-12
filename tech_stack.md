# 🛠️ 대기오염 매핑 및 분석 서비스 초기 기술 스택 명세서 (Technology Stack Specification)

본 문서는 AIHub 위성 분석 데이터와 에어코리아 실시간 측정소 데이터를 결합하여 지리 공간 시각화를 제공하는 **대기오염 배출원 매핑 서비스**의 초기 기술 스택 및 아키텍처 구성을 문서화한 것입니다.

---

## 1. 🏗️ 서비스 시스템 아키텍처

본 서비스는 가볍고 빠르게 확장할 수 있는 **Full-Python 기반의 2-Tier 아키텍처**를 채택하고 있습니다.

```mermaid
graph TD
    subgraph "Frontend Layer (Dashboard)"
        F1["Streamlit Application"] <-->|HTTP / REST| B1
        F1 -->|Map Rendering| F2["Folium / streamlit-folium"]
        F1 -->|Dynamic Charts| F3["Plotly"]
    end

    subgraph "Backend Layer (API Services)"
        B1["FastAPI Application (Uvicorn)"]
        B2["Data Importer / Spatial Parser (rasterio, Shapely)"] -->|Data Processing| B1
    end

    subgraph "Data & External API Layer"
        D1[("MongoDB Atlas (Cloud)")] <-->|PyMongo| B1
        E1["Air Korea Open API"] <-->|HTTPX (Async)| B1
        AI1["AIHub Satellite Data (.json, .tif)"] -->|Local File Parse| B2
    end
```

---

## 2. 🗂️ 레이어별 상세 기술 스택

### 1️⃣ Web Frontend (시각화 및 대시보드)
* **Streamlit (`streamlit>=1.24.0`)**
  - **도입 목적:** 복잡한 HTML/JS/CSS 프레임워크 도입 없이 Python 코드 기반으로 고성능 데이터 대시보드를 빠르게 프로토타이핑하고 실시간 상태를 동기화하기 위해 사용합니다.
  - **핵심 역할:** 사이드바 필터링, 대기 오염 수치 비교 차트 렌더링, 지도 결합 화면 제어.
* **Folium & Streamlit-Folium (`folium>=0.14.0`, `streamlit-folium>=0.12.0`)**
  - **도입 목적:** Leaflet.js 라이브러리를 Python에서 간편히 조작하여 강력한 대화형 지도를 생성합니다.
  - **핵심 역할:** 위성 분석 기반의 산업단지 Polygon 경계 표시 및 개별 굴뚝 배출원 Point 마커 핀 투영, 에어코리아 측정소 반경 및 실시간 대기 등급별 색상 매핑.
* **Plotly (`plotly>=5.15.0`)**
  - **도입 목적:** 미려하고 인터랙티브한 반응형 시계열 및 막대그래프 시각화.
  - **핵심 역할:** 특정 공단/측정소의 PM10, SO2, CO 등 오염 물질 농도 트렌드 그래프 표출.

### 2️⃣ Web Backend (API 서비스 및 가공)
* **FastAPI (`fastapi>=0.100.0`)**
  - **도입 목적:** 비동기(ASGI) 아키텍처 기반으로 높은 동시 요청 처리 성능을 확보하고 OpenAPI 스펙을 자동 생성합니다.
  - **핵심 역할:** 에어코리아 대기질 실시간 API Proxy 제공, MongoDB 데이터 조회용 RESTful API 서빙.
* **Uvicorn (`uvicorn>=0.22.0`)**
  - **도입 목적:** 초경량, 고성능 ASGI 웹 서버.
  - **핵심 역할:** 백엔드 FastAPI 애플리케이션의 런타임 구동 엔진.
* **HTTPX (`httpx>=0.24.1`)**
  - **도입 목적:** 표준 `requests` 모듈과 다르게 완벽한 비동기(async/await) HTTP 요청을 지원합니다.
  - **핵심 역할:** 에어코리아 공공 API 호출 시 블로킹 없이 병렬 및 비동기 방식으로 응답을 수집하여 속도 최적화.

### 3️⃣ Database Layer (데이터베이스 및 영속성)
* **MongoDB Atlas (`pymongo[srv]>=4.3.3`)**
  - **도입 목적:** GeoJSON 포맷의 공간 정보를 기본적으로 인식하여 강력한 지리 공간 쿼리(Spatial Query, 예: `$near`, `$geoWithin`)를 수행할 수 있고, 스키마 유연성을 제공하는 완전 복제형 클라우드 NoSQL 데이터베이스입니다.
  - **핵심 역할:** 위성 기반의 굴뚝 검출 BBOX/LINE 속성 및 GeoTIFF Bounds, 실시간 에어코리아 측정소 메타데이터 저장 및 쿼리.
* **dnspython (`dnspython>=2.3.0`)**
  - **도입 목적:** MongoDB Atlas의 `mongodb+srv://` 연결 URI 프로토콜을 올바르게 해석하고 DNS 확인 처리를 지원하기 위한 필수 유틸리티.

### 4️⃣ Data Processing & Geospatial Analysis (공간 및 데이터 분석)
* **Shapely (`shapely>=2.0.1`)**
  - **도입 목적:** Python의 사실상 표준 공간 기하학 엔진으로 다양한 기하학적 도형 연산을 수행합니다.
  - **핵심 역할:** GeoTIFF의 외곽 사각형 바운즈(Bounding Box)를 정합성 있는 다각형(Polygon) 객체로 생성 및 위도/경도 WGS84 검증.
* **Pandas (`pandas>=2.0.0`)**
  - **도입 목적:** 시계열 데이터 프레임 핸들링 및 고성능 연산.
  - **핵심 역할:** 측정소 데이터 병합, 이상치 정제 및 일평균/시간대별 통계량 요약.
* **Rasterio (추천/도입 예정)**
  - **도입 목적:** 위성 TIF 포맷(GeoTIFF) 파일에 인코딩된 메타데이터 공간 좌표 좌표계(CRS) 정보를 해독합니다.
  - **핵심 역할:** `.tif` 파일의 바이트 스트림으로부터 지리 경계 위도/경도(WGS84 Bounds) 값을 추출하여 맵 좌표계로 매핑.

### 5️⃣ Configuration & Environment (환경 설정)
* **Pydantic & Pydantic-Settings (`pydantic>=2.0`, `pydantic-settings>=2.0`)**
  - **도입 목적:** 데이터 구조 정의 및 엄격한 타입 검증과 `BaseSettings`를 통한 환경 설정 관리.
  - **핵심 역할:** API 요청 본문 직렬화 및 `.env` 파일과 시스템 환경 변수의 동적 파싱 및 안전한 설정 클래스 바인딩.
* **python-dotenv (`python-dotenv>=1.0.0`)**
  - **도입 목적:** 로컬 및 배포 단계에서 환경 변수를 효율적으로 파일화하여 관리.
  - **핵심 역할:** MongoDB URI, Air Korea API KEY 등 자격 증명을 로컬 환경 변수에 바인딩.

---

## 3. ⚙️ 로컬 환경 구성 가이드

### 1) 가상환경 생성 및 패키지 설치
```bash
# 가상환경 구축
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 필수 패키지 일괄 설치
pip install -r requirements.txt
```

### 2) 환경 변수 파일 생성 (`.env`)
프로젝트 루트 폴더에 `.env` 파일을 생성하고 아래 형식을 맞추어 설정 정보를 기록합니다.
```env
# MongoDB Atlas Configuration
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=air_pollution_db

# Air Korea Open API Key
AIRKOREA_API_KEY=your_airkorea_api_key_here

# Application Environments
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

---

## 4. 🚀 운영 서버 직접 배포 가이드 (Direct Server Setup)

본 서비스는 Docker를 사용하지 않고 운영 가상 서버(Ubuntu 등)에 직접 배포되어 구동하는 비-도커(Non-Docker) 아키텍처를 완벽하게 지원합니다.

### 1) 시스템 의존성 설치
지리 분석 라이브러리(`rasterio`, `shapely`)의 C-library 컴파일을 보장하기 위해 리눅스 패키지를 선행 설치합니다.
```bash
sudo apt-get update && sudo apt-get install -y build-essential python3-dev python3-venv libgdal-dev
```

### 2) 배포 환경 통합 스크립트 실행
프로젝트 루트 폴더 내 `deploy.sh` 스크립트를 기동하여 가상환경 세팅 및 모듈 설치를 자동 완료합니다.
```bash
./deploy.sh
```

### 3) Systemd 서비스 등록 (무중단 상시 기동)
터미널 세션 종료 후에도 서비스가 안정적으로 상시 기동되도록 아래와 같이 서비스 유닛을 등록합니다.

* **Streamlit 프론트엔드 서비스 (`/etc/systemd/system/ecomap-frontend.service`):**
  - 작업 디렉토리 내의 가상환경 streamlit 실행 주소를 연결하여 `8501` 포트로 구동 및 자가 재기동 처리.
* **FastAPI 백엔드 서비스 (`/etc/systemd/system/ecomap-backend.service`):**
  - Uvicorn을 사용하여 `8000` 포트로 API 서빙 및 상시 백그라운드 구동.

```bash
# 서비스 정의 등록 및 실행
sudo cp ecomap-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ecomap-frontend.service
sudo systemctl enable --now ecomap-backend.service
```

