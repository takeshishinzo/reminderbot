from models import Reminders, Users
from database import Base, engine
import asyncio
async def main():   
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Таблица создана")

asyncio.run(main())
