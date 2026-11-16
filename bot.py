import asyncio

from aiogram import Dispatcher

from handlers import router

from services import bot, start_scheduler

dp = Dispatcher()

dp.include_router(router)

async def main():
    await start_scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

