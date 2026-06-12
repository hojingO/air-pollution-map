import json
import logging
import math
from pathlib import Path
from pymongo import MongoClient, GEOSPHERE
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from backend.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB-Connector")

FALLBACK_FILE = Path(__file__).parent / "fallback_db.json"

class FallbackDatabase:
    """MongoDB가 작동하지 않을 때 사용하는 로컬 JSON 파일 기반의 Smart Fallback Database"""
    def __init__(self):
        self.file_path = FALLBACK_FILE
        self.data = {"pollution_sources": [], "air_quality_stations": [], "air_quality_logs": []}
        self.load_data()

    def load_data(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"💾 [Fallback DB] 로컬 데이터를 로드했습니다. ({self.file_path})")
            except Exception as e:
                logger.error(f"❌ [Fallback DB] 로컬 데이터 로드 실패: {e}")
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ [Fallback DB] 로컬 데이터 저장 실패: {e}")

    def insert_one(self, collection_name, doc):
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        self.data[collection_name].append(doc)
        self.save_data()
        return doc

    def insert_many(self, collection_name, docs):
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            self.data[collection_name].append(doc)
        self.save_data()
        return docs

    def find(self, collection_name, query=None, limit=0):
        docs = self.data.get(collection_name, [])
        # 간단한 쿼리 매칭 (e.g. {"station_name": "xxx"})
        filtered = []
        for doc in docs:
            match = True
            if query:
                for k, v in query.items():
                    # GeoSpatial 쿼리는 따로 공간 검색 로직으로 처리
                    if k.startswith("$") or isinstance(v, dict):
                        continue
                    if doc.get(k) != v:
                        match = False
                        break
            if match:
                filtered.append(doc)
        
        if limit > 0:
            filtered = filtered[:limit]
        return filtered

    def delete_many(self, collection_name, query=None):
        if not query:
            self.data[collection_name] = []
        else:
            docs = self.data.get(collection_name, [])
            remaining = []
            for doc in docs:
                match = True
                for k, v in query.items():
                    if doc.get(k) != v:
                        match = False
                        break
                if not match:
                    remaining.append(doc)
            self.data[collection_name] = remaining
        self.save_data()
        return len(self.data[collection_name])

# Haversine 공식을 사용한 고정밀 오프라인 공간 쿼리 구현 (모듈 레벨 함수로 분리)
def haversine_distance(lon1, lat1, lon2, lat2):
    R = 6371000.0  # 지구 반지름 (미터 단위)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
    return R * c

    def find_nearest_stations(self, lon, lat, max_distance_meters=20000):
        stations = self.data.get("air_quality_stations", [])
        results = []
        for st in stations:
            st_lon, st_lat = st["location"]["coordinates"]
            dist = haversine_distance(lon, lat, st_lon, st_lat)
            if dist <= max_distance_meters:
                results.append({
                    "station": st,
                    "distance": dist
                })
        # 거리 기준 오름차순 정렬
        results.sort(key=lambda x: x["distance"])
        return results


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_fallback = False
        self.fallback_db = None
        self.connect()

    def connect(self):
        try:
            logger.info("🔌 MongoDB 연결을 시도합니다...")
            # 5초 타임아웃 설정으로 느린 네트워크 환경에서 안정성 확보
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # 연결 상태 강제 확인
            self.client.admin.command('ping')
            self.db = self.client[settings.DB_NAME]
            self.is_fallback = False
            logger.info("✅ MongoDB 연결 성공! 2dsphere 공간 인덱스를 생성합니다.")
            self.create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(f"⚠️ MongoDB 연결 실패 (폴백 모드 전환): {e}")
            self.is_fallback = True
            self.fallback_db = FallbackDatabase()
            logger.info("💾 Smart Fallback 로컬 데이터베이스가 활성화되었습니다.")

    def create_indexes(self):
        if not self.is_fallback:
            try:
                # 배출원 및 측정소에 GeoSpatial 2dsphere 인덱스 생성
                self.db["pollution_sources"].create_index([("location", GEOSPHERE)])
                self.db["air_quality_stations"].create_index([("location", GEOSPHERE)])
                # 로그 조회 최적화를 위해 복합 인덱스 생성
                self.db["air_quality_logs"].create_index([("station_name", 1), ("data_time", -1)])
                logger.info("✨ MongoDB 2dsphere 및 복합 인덱스 생성 완료.")
            except Exception as e:
                logger.error(f"❌ 인덱스 생성 실패: {e}")

    # 공통 데이터베이스 인터페이스 설계
    def insert_one(self, collection, doc):
        if self.is_fallback:
            return self.fallback_db.insert_one(collection, doc)
        return self.db[collection].insert_one(doc)

    def insert_many(self, collection, docs):
        if self.is_fallback:
            return self.fallback_db.insert_many(collection, docs)
        if not docs:
            return []
        return self.db[collection].insert_many(docs)

    def find(self, collection, query=None, limit=0, sort=None):
        if query is None:
            query = {}
        if self.is_fallback:
            docs = self.fallback_db.find(collection, query, limit)
            if sort:
                # 간단한 정렬 지원 (필요 시)
                field, direction = sort[0]
                reverse = True if direction == -1 else False
                docs.sort(key=lambda x: x.get(field, ""), reverse=reverse)
            return docs
        
        cursor = self.db[collection].find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)

    def find_one(self, collection, query=None, sort=None):
        if query is None:
            query = {}
        if self.is_fallback:
            docs = self.fallback_db.find(collection, query, limit=1)
            return docs[0] if docs else None
        
        if sort:
            cursor = self.db[collection].find(query).sort(sort).limit(1)
            results = list(cursor)
            return results[0] if results else None
        return self.db[collection].find_one(query)

    def delete_many(self, collection, query=None):
        if query is None:
            query = {}
        if self.is_fallback:
            return self.fallback_db.delete_many(collection, query)
        return self.db[collection].delete_many(query).deleted_count

    # 특정 좌표 기준 최단 거리의 측정소 찾기
    def get_nearest_stations(self, lon, lat, max_distance_meters=20000, limit=5):
        if self.is_fallback:
            results = self.fallback_db.find_nearest_stations(lon, lat, max_distance_meters)
            return results[:limit]
        
        # MongoDB 2dsphere 지리 쿼리 ($near 연산자 사용)
        query = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "$maxDistance": max_distance_meters
                }
            }
        }
        
        stations = list(self.db["air_quality_stations"].find(query).limit(limit))
        results = []
        for station in stations:
            # MongoDB $near 쿼리는 거리를 자동 반환하지 않으므로 Haversine 직접 산출
            st_lon, st_lat = station["location"]["coordinates"]
            dist = haversine_distance(lon, lat, st_lon, st_lat)
            results.append({
                "station": station,
                "distance": dist
            })
        return results

# 싱글톤 인스턴스 생성
db_manager = DatabaseManager()
