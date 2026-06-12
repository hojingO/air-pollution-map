import os
import datetime
import logging
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.transform import from_origin
from shapely.geometry import box
from backend.database import db_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Geospatial-Importer")

# 프로젝트 루트 및 데이터 경로 정의
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
LS30_DIR = DATA_DIR / "VL_LS30"
SN10_DIR = DATA_DIR / "VL_SN10"


def generate_sample_tifs_if_empty():
    """
    데이터 디렉토리가 비어있거나 KOR TIF 파일이 없을 경우,
    개발자 테스트를 돕기 위해 유효한 한국 산업단지 좌표계를 가진 샘플 GeoTIFF 파일을 자동 생성합니다.
    """
    os.makedirs(LS30_DIR, exist_ok=True)
    os.makedirs(SN10_DIR, exist_ok=True)

    # 1. Landsat (VL_LS30) 샘플 생성 (시화반월단지 근처: Center [126.76, 37.31])
    ls30_files = list(LS30_DIR.glob("*KOR*.tif"))
    if not ls30_files:
        logger.info("ℹ️ [Sample-Gen] VL_LS30 폴더 내 한국 영토 TIF 파일이 발견되지 않아 시화반월단지 샘플을 생성합니다.")
        sample_path = LS30_DIR / "LS30_KOR_Sihwa_Industrial_Complex.tif"
        
        # 10x10 사이즈의 가상 분류 그리드 생성
        data = np.random.randint(1, 4, size=(10, 10)).astype(rasterio.uint8)
        
        # 중심 경도 126.76, 위도 37.31 기준 약 0.04도 범위 (가로/세로)
        size_deg = 0.04
        res = size_deg / 10.0
        transform = from_origin(126.76 - size_deg/2.0, 37.31 + size_deg/2.0, res, res)
        
        with rasterio.open(
            sample_path,
            'w',
            driver='GTiff',
            height=10,
            width=10,
            count=1,
            dtype=data.dtype,
            crs='EPSG:4326',
            transform=transform
        ) as dst:
            dst.write(data, 1)
        logger.info(f"✨ [Sample-Gen] Landsat 샘플 생성 성공: {sample_path.name}")

    # 2. Sentinel-2 (VL_SN10) 샘플 생성 (울산석유화학단지 근처: Center [129.36, 35.51])
    sn10_files = list(SN10_DIR.glob("*KOR*.tif"))
    if not sn10_files:
        logger.info("ℹ️ [Sample-Gen] VL_SN10 폴더 내 한국 영토 TIF 파일이 발견되지 않아 울산단지 샘플을 생성합니다.")
        sample_path = SN10_DIR / "SN10_KOR_Ulsan_Petrochemical_Complex.tif"
        
        # 10x10 사이즈의 가상 분류 그리드 생성
        data = np.random.randint(1, 4, size=(10, 10)).astype(rasterio.uint8)
        
        # 중심 경도 129.36, 위도 35.51 기준 약 0.02도 범위
        size_deg = 0.02
        res = size_deg / 10.0
        transform = from_origin(129.36 - size_deg/2.0, 35.51 + size_deg/2.0, res, res)
        
        with rasterio.open(
            sample_path,
            'w',
            driver='GTiff',
            height=10,
            width=10,
            count=1,
            dtype=data.dtype,
            crs='EPSG:4326',
            transform=transform
        ) as dst:
            dst.write(data, 1)
        logger.info(f"✨ [Sample-Gen] Sentinel-2 샘플 생성 성공: {sample_path.name}")


class GeospatialImporter:
    def __init__(self):
        self.imported_count = 0

    def parse_tif_geometery(self, file_path: Path):
        """
        rasterio를 사용하여 TIF 파일의 메타데이터 및 지리 Bounds를 해독하고,
        표준 위도/경도(WGS84, EPSG:4326) Polygon GeoJSON으로 변환합니다.
        """
        try:
            with rasterio.open(file_path) as src:
                # 1. 파일의 기본 지리 경계 읽기
                left, bottom, right, top = src.bounds
                crs = src.crs

                if not crs:
                    logger.warning(f"⚠️ [Importer] {file_path.name} 파일에 CRS(좌표계) 정보가 누락되었습니다. 기본 EPSG:4326으로 진행합니다.")
                    crs = "EPSG:4326"

                # 2. 좌표계를 표준 경위도(WGS84, EPSG:4326)로 변환 (좌표 변환이 필요한 경우 자동 처리)
                if str(crs).upper() != "EPSG:4326":
                    logger.info(f"🔄 [Importer] {file_path.name} 좌표계 변환: {crs} -> EPSG:4326")
                    left, bottom, right, top = transform_bounds(crs, "EPSG:4326", left, bottom, right, top)

                # 3. shapely를 사용하여 Polygon 구조 생성
                geom_box = box(left, bottom, right, top)
                
                # 외곽 고리(Exterior coordinates) 추출하여 GeoJSON 규격에 맞게 닫힌 루프(List of Lists)로 변환
                coords_list = [list(pt) for pt in geom_box.exterior.coords]
                
                geojson_polygon = {
                    "type": "Polygon",
                    "coordinates": [coords_list]
                }
                
                resolution = "30m" if "LS30" in str(file_path) else "10m"
                satellite_name = "Landsat-8" if "LS30" in str(file_path) else "Sentinel-2"

                # 산단 구역 필터링과 정상 연동되도록 파일명 기준 한국 산단명 매핑
                region_name = ""
                if "Sihwa" in file_path.name:
                    region_name = "시화반월단지"
                elif "Ulsan" in file_path.name:
                    region_name = "울산석유화학단지"

                address = f"대한민국 주요 산업지역 ({region_name} 산단 내 위성 분석 구역)" if region_name else f"대한민국 위성 분석 구역 ({satellite_name} {resolution} 마스크)"

                return {
                    "name": file_path.stem.replace("_sample", ""),
                    "source_type": "satellite_area",
                    "location": geojson_polygon,
                    "address": address,
                    "satellite_metadata": {
                        "satellite_name": satellite_name,
                        "band_type": "Land Classification Mask",
                        "pixel_resolution": resolution,
                        "observation_value": float(np.random.uniform(0.7, 0.95)), # 가상 대기 분류 마스크 정밀도 매핑
                        "confidence": float(np.random.uniform(0.85, 0.99)),
                        "original_filename": file_path.name,
                        "crs": str(crs),
                        "bounds": [left, bottom, right, top]
                    },
                    "created_at": datetime.datetime.utcnow()
                }
        except Exception as e:
            logger.error(f"❌ [Importer] {file_path.name} 파싱 실패: {e}")
            return None

    def run_import(self):
        """
        데이터 폴더에서 한국 영토 TIF 파일을 읽어와 데이터베이스에 적재합니다.
        기존에 적재되어 있던 위성 데이터 영역(satellite_area)은 중복 방지를 위해 삭제 후 새로 구축합니다.
        """
        logger.info("🚀 [Importer] 대기오염 위성 TIF 데이터 임포트 파이프라인 가동 시작...")
        
        # 1단계: 샘플 TIF 검사 및 자동 빌드
        generate_sample_tifs_if_empty()

        # 2단계: 대상 파일 스캔
        target_files = list(LS30_DIR.glob("*KOR*.tif")) + list(SN10_DIR.glob("*KOR*.tif"))
        logger.info(f"📂 [Importer] 총 {len(target_files)}개의 한국 영토 실측 TIF 파일이 감지되었습니다.")

        imported_docs = []
        for file_path in target_files:
            logger.info(f"📖 [Importer] 파일 파싱 중: {file_path.name}")
            doc = self.parse_tif_geometery(file_path)
            if doc:
                imported_docs.append(doc)

        if not imported_docs:
            logger.warning("⚠️ [Importer] 적재할 유효한 위성 데이터 영역이 존재하지 않습니다.")
            return 0

        # 3단계: 기존 DB 적재 내역 중 'satellite_area' 유형만 선별 삭제 (멱등성 확보)
        deleted_count = db_manager.delete_many("pollution_sources", {"source_type": "satellite_area"})
        logger.info(f"🧹 [Importer] 기존 DB에 누적된 satellite_area 데이터 {deleted_count}건을 정리하였습니다.")

        # 4단계: 신규 추출 데이터 적재
        db_manager.insert_many("pollution_sources", imported_docs)
        self.imported_count = len(imported_docs)
        logger.info(f"💾 [Importer] 총 {self.imported_count}건의 위성 영역 데이터가 성공적으로 적재되었습니다! (DB Mode: {'Fallback DB' if db_manager.is_fallback else 'MongoDB Atlas'})")

        return self.imported_count


if __name__ == "__main__":
    importer = GeospatialImporter()
    importer.run_import()
