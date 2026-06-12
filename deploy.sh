#!/usr/bin/env bash

# ==============================================================================
# EcoMap 배포 및 자동 초기화 스크립트 (deploy.sh)
# ==============================================================================

set -e

# 색상 터미널 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN} 🛰️  EcoMap 서비스 배포 자동화 및 환경 셋업을 시작합니다.${NC}"
echo -e "${GREEN}======================================================================${NC}"

# 1. OS 의존성 패키지 설치 가이드 (Debian/Ubuntu 계열 기준)
if [ -f /etc/debian_version ]; then
    echo -e "\n${YELLOW}[Step 1] OS 패키지 의존성을 확인하고 설치합니다 (sudo 권한 필요)...${NC}"
    sudo apt-get update
    sudo apt-get install -y build-essential python3-dev python3-venv libgdal-dev
else
    echo -e "\n${YELLOW}[Step 1] Debian/Ubuntu 계열 외의 OS입니다. 아래 OS 의존성이 이미 설치되어 있는지 확인하세요:${NC}"
    echo -e " - build-essential, python3-dev, python3-venv, libgdal-dev (GDAL C-library)"
fi

# 2. 가상환경 구성
echo -e "\n${YELLOW}[Step 2] Python3 가상환경(venv)을 생성합니다...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ venv 가상환경이 성공적으로 생성되었습니다.${NC}"
else
    echo -e "💡 기존 venv 가상환경이 존재하여 재사용합니다."
fi

# 3. 가상환경 활성화 및 pip 업그레이드
source venv/bin/activate
echo -e "\n${YELLOW}[Step 3] pip 및 setuptools를 업그레이드합니다...${NC}"
pip install --upgrade pip setuptools wheel

# 4. requirements.txt 패키지 설치
echo -e "\n${YELLOW}[Step 4] requirements.txt에 정의된 Python 패키지를 설치합니다...${NC}"
echo -e "   (rasterio, shapely 빌드는 GDAL 및 시스템 컴파일러에 의존하므로 다소 시간이 걸릴 수 있습니다.)"
pip install -r requirements.txt
echo -e "${GREEN}✅ 모든 Python 의존성이 설치되었습니다.${NC}"

# 5. .env 설정 유무 체크
echo -e "\n${YELLOW}[Step 5] .env 환경 설정 파일을 검증합니다...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env 파일이 존재하지 않습니다. 로컬 환경 설정을 복사하여 기본형을 생성합니다.${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        # 기본 .env 생성
        cat <<EOT > .env
# MongoDB Atlas 연결 URI (본인의 Atlas 연결 주소로 교체하세요)
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/air_pollution?retryWrites=true&w=majority
DB_NAME=air_pollution

# 에어코리아 API 인증키
AIRKOREA_SERVICE_KEY=your_airkorea_api_key_here

# FastAPI 설정
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
EOT
    fi
    echo -e "${RED}❌ .env 파일이 자동으로 구성되었습니다. 반드시 파일 내의 MONGODB_URI와 AIRKOREA_SERVICE_KEY를 실제 자격 증명으로 교체한 후 서비스를 실행하세요.${NC}"
else
    echo -e "${GREEN}✅ .env 파일이 이미 존재합니다.${NC}"
fi

# 6. 배출원 데이터 파이프라인(TIF/JSON 임포터) 사전 검증 테스트
echo -e "\n${YELLOW}[Step 6] MongoDB 연결 및 임포터 엔진 자가 진단을 수행합니다...${NC}"
export PYTHONPATH=$PWD
python3 -c "
import os
from backend.database import db_manager
if db_manager.is_fallback:
    print('\033[1;33m[Warning] MongoDB Atlas 연결 실패. 로컬 Fallback DB 모드로 작동합니다. .env 설정을 재확인하세요.\033[0m')
else:
    print('\033[0;32m[Success] MongoDB Atlas 연결이 정상 확인되었습니다.\033[0m')
"

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN} 🎉 셋업 완료! 아래 명령어로 systemd 서비스 등록을 실행해 주세요.${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "1. 서비스 설정 파일의 절대 경로(/home/ubuntu/air-pollution-map 등)가 올바른지 검토한 후 복사합니다:"
echo -e "   ${YELLOW}sudo cp ecomap-frontend.service /etc/systemd/system/${NC}"
echo -e "   ${YELLOW}sudo cp ecomap-backend.service /etc/systemd/system/${NC}"
echo -e ""
echo -e "2. systemd 데몬을 재로드하고 서비스를 기동 및 자동 시작 등록합니다:"
echo -e "   ${YELLOW}sudo systemctl daemon-reload${NC}"
echo -e "   ${YELLOW}sudo systemctl enable --now ecomap-frontend.service${NC}"
echo -e "   ${YELLOW}sudo systemctl enable --now ecomap-backend.service${NC}"
echo -e ""
echo -e "3. 서비스 동작 로그를 확인합니다:"
echo -e "   ${YELLOW}sudo journalctl -u ecomap-frontend.service -f${NC}"
echo -e "${GREEN}======================================================================${NC}"
