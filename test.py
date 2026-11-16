import asyncio
import services
from datetime import datetime, timedelta
from rich import print


async def main():
    await services.create_user(111)
    await services.add_date_reminder(111,"aa1aa",datetime.now()+timedelta(seconds=15))
    await services.add_date_reminder(111,"aa2aa",datetime.now()+timedelta(seconds=18))
    await asyncio.sleep(120)

asyncio.run(main())