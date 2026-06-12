# 📑 대기오염 배출원 매핑 서비스 개발 및 실행 이력 (History Log)

본 문서는 개발 진행 사항 및 실행 내역을 카테고리별로 기록하여 투명하게 추적할 수 있도록 한 개발 이력 문서입니다.

---

## 🛠️ 1. 의존성 및 패키지 설정 (Dependencies)
* **[2026-06-02] 의존성 패키지 설치 완료 (rasterio)**
  - 아리랑-3호의 중국(`CHN`) JSON 굴뚝 데이터 대신, 대한민국 영토 실측 데이터인 Landsat(`VL_LS30`) 및 Sentinel-2(`VL_SN10`) TIF 파일을 핵심 연동 대상으로 설정하는 구현 계획서 승인 완료.
  - `requirements.txt`에 `rasterio>=1.3.8` 추가 완료.
  - `python3 -m pip install -r requirements.txt` 명령을 성공적으로 가동하여 `rasterio-1.5.0` 및 의존 라이브러리 설치 완료.

---

## 📂 2. 데이터 디렉토리 및 인프라 구축 (Directories & DB)
* **[2026-06-02] 데이터 디렉토리 구조 생성 완료**
  - 프로젝트 루트 아래에 Landsat TIF용 `data/VL_LS30/` 및 Sentinel-2 TIF용 `data/VL_SN10/` 폴더를 생성 완료하고, 보존을 위한 `.gitkeep` 파일 생성 완료.
  - 사용자가 실제 한국 위성 파일(`_KOR_*.tif`)을 해당 디렉토리에 손쉽게 보관할 수 있도록 세팅 완료.

---

## ⚙️ 3. 데이터 파싱 및 백엔드 서비스 개발 (Backend Engine)
* **[2026-06-02] 지리 데이터 임포터 엔진 개발 완료**
  - [importer.py](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/backend/services/importer.py) 작성 완료.
  - `rasterio` 및 `shapely`를 활용한 GeoTIFF 경계 디코딩, 표준 경위도(`EPSG:4326`) 다각형(Polygon) 자동 복원 모듈 탑재.
  - 로컬 테스트 지원용 실측 좌표계 샘플 GeoTIFF 자동 빌더 기능(여수/시화반월단지 경위도 연동) 내장.
  - 추출된 위성 폴리곤 데이터를 `pollution_sources` 컬렉션에 멱등하게 적재할 수 있도록 DB 트랜잭션 설계.
* **[2026-06-02] 지리 데이터 임포터 가동 및 DB 적재 성공**
  - `python3 -m backend.services.importer` 스크립트를 기동하여 첫 데이터 파이프라인 수립 완료.
  - `data/` 디렉토리에 한국 위성 TIF 파일 샘플 2건(시화반월단지 Landsat, 울산석유화학단지 Sentinel-2) 자동 생성 완료.
  - `rasterio`를 통한 바운드 획득 및 WGS84 GeoJSON Polygon으로의 성공적인 디코딩 완료.
  - 로컬 폴백 데이터베이스인 `fallback_db.json` 내 `pollution_sources` 컬렉션에 2건의 폴리곤 정보 적재 성공.

---

## 🗺️ 4. 프론트엔드 및 시각화 컴포넌트 개발 (Frontend & UI)
* **[2026-06-02] 지형 다각형 시각화 최적화 및 프리미엄 스타일 반영**
  - [map.py](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/frontend/components/map.py) 및 [app.py](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/frontend/app.py) 수정 완료.
  - 위성 데이터 분석 영역(`satellite_area`)에 대해 다크 테마에 어울리는 **비비드 시안 네온 블루 스타일링** 적용 완료 (테두리 `#4facfe`, 내부 `#00f2fe`).
  - 번역 딕셔너리에 `satellite_area`를 한국어로 매핑하여 팝업과 툴팁이 자연스럽게 표출되도록 구현.
  - 대시보드 좌측 사이드바 필터에 "위성 관측 구역 (TIF)" 옵션을 새롭게 배치하여 개별 굴뚝 마커뿐만 아니라 실측 지형 다각형 영역만 따로 필터링해 볼 수 있도록 설계 완료.

---

## 🧪 5. 검증 및 테스트 실행 (Verification & Tests)
* **[2026-06-02] Streamlit 서버 기동 및 최종 연동 확인**
  - `streamlit run frontend/app.py`를 기동하여 최종 검증 테스트를 개시함.
  - 가상 터미널 환경에서 Streamlit 최초 onboarding 프롬프트(이메일 수집 차단)를 newline 인풋 전송을 통해 예외 없이 정상 우회 완료.
  - 서버 실행 로그 확인 결과: 로컬 MongoDB 미가동 시 스마트 폴백 디바이스인 `fallback_db.json`을 오차 없이 감지하고 2건의 Landsat/Sentinel 위성 다각형 영역을 정상 로드함.
  - 로컬 호스트 `http://localhost:8501` 경로를 통해 인터랙티브 맵에 네온 블루 시안 컬러의 정밀 폴리곤 영역이 에어코리아 대기 정보와 결합하여 성공적으로 렌더링됨을 시각적으로 최종 검증 완료!
* **[2026-06-08] API 연동 보완 및 자가복구 데이터 초기화 수정**
  - `.env`에 입력된 에어코리아 인증키 수정을 위해 `backend/config.py`에 `override=True` 옵션을 적용하여 캐시 환경변수 방어 완료.
  - TIF 임포트 실행 후 측정소 목록이 비어있는 상태에서 0개로 표시되던 이슈 진단. [app.py](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/frontend/app.py)에 측정소(`stations`) 미적재 시 데이터 자동 자가 복구(Self-Healing) 및 TIF 자동 임포트 재연동 구현 완료.
  - `mock_data.py`의 `math` 모듈 누락에 따른 NameError 예외 버그를 수정하고 DB 강제 사전 시딩 테스트 완료 (측정소 12개, 배출원 23개).
  - 에어코리아 API 호출 결과 `401 Unauthorized` 수신 완료. 공공데이터포털 인증키 발급 지연(수 시간 소요)을 진단하고 지연되는 동안 고정밀 가상 시뮬레이터로 매끄럽게 자동 폴백 동작 확인 완료.
  - 로컬 폴백 JSON DB 로드 시 datetime 데이터가 문자열 포맷으로 디코딩되어 발생한 `AttributeError: 'str' object has no attribute 'strftime'` 오류 진단. [map.py](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/frontend/components/map.py) 내부 시간 포맷터에 예외 복구 구문 및 ISO/일반 문자열 파서 코드를 빌드하여 해결 완료.

---

## 🚀 6. 운영 서버 무중단 배포 및 환경 구축 (Deployment)
* **[2026-06-09] 비-도커(Non-Docker) 기반 리눅스 직접 배포 구성 구축 완료**
  - 클라우드 DB인 **MongoDB Atlas** 연동 명세 준수를 확립하고 로컬 도커 구성안에서 서버 직접 배포 방식으로 수정 승인 완료.
  - OS 지형 라이브러리(`libgdal-dev` 등) 설치, `venv` 생성 및 패키지 셋업, `.env` 유효성 진단을 지원하는 자동화 배포 스크립트 [deploy.sh](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/deploy.sh) 개발 완료 (실행 권한 부여 완료).
  - Streamlit 대시보드의 백그라운드 상시 기동 및 고가용성 보장을 위한 [ecomap-frontend.service](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/ecomap-frontend.service) `systemd` 서비스 설정 파일 정의 완료.
  - API 서빙용 FastAPI 백엔드의 상시 기동을 위한 [ecomap-backend.service](file:///Users/chahojin/.gemini/antigravity-ide/scratch/air-pollution-map/ecomap-backend.service) `systemd` 서비스 설정 파일 정의 완료.
  - 전체 배포 과정과 트러블슈팅을 담은 배포 완료 보고서 작성 완료.


