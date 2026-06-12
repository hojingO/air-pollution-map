import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.config import settings
from backend.services.airkorea import airkorea_client

async def main():
    print(f"Loaded API Key: {settings.AIRKOREA_SERVICE_KEY[:10]}...{settings.AIRKOREA_SERVICE_KEY[-10:] if len(settings.AIRKOREA_SERVICE_KEY) > 10 else ''}")
    print(f"Is Configured: {airkorea_client.is_configured}")
    
    # Try requesting real-time data for "정왕동" (Siheung region)
    station = "정왕동"
    print(f"\n📡 Requesting real-time air quality data for station: '{station}'...")
    
    # We will temporarily bypass cache by forcing API call logic if we want to be sure,
    # but since this is a new run, there's no cache for today's time in the database yet.
    result = await airkorea_client.get_realtime_air_quality(station)
    print("\nResult received:")
    for k, v in result.items():
        if k != "_id": # Skip MongoDB object ID for print readability
            print(f"  - {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
