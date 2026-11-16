from aiogram import Bot
from aiogram.types import Message

from config import TOKEN
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlalchemy import func, select, delete
from sqlalchemy.orm import selectinload

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dateutil import parser

from database import Session
from models import Users, Reminders

from rich import print

bot = Bot(token=TOKEN)

scheduler = AsyncIOScheduler(timezone="UTC")

#адаптация парсера под русский
class ru_parserinfo(parser.parserinfo):

    AMPM = [
    ('am', 'a', 'утра'),
    ('pm', 'p', 'вечера', 'дня')
    ]

    HMS = [
        ('ч', 'час', 'часа', 'часов'),
        ('м', 'мин', 'минута', 'минуты', 'минут'),
        ('с', 'сек', 'секунда', 'секунды', 'секунд')
    ]

    JUMP = [
        ' ', '.', ',', ';', '-', '/', "'",
        'в', 'во', 'на', 'и', 'г', 'г.', 'года', 'год',
        'от', 'до'
    ]

    MONTHS = [
        ('янв', 'январь', 'января'),
        ('фев', 'февраль', 'февраля'),
        ('мар', 'март', 'марта'),
        ('апр', 'апрель', 'апреля'),
        ('май', 'мая'),
        ('июн', 'июнь', 'июня'),
        ('июл', 'июль', 'июля'),
        ('авг', 'август', 'августа'),
        ('сен', 'сент', 'сентябрь', 'сентября'),
        ('окт', 'октябрь', 'октября'),
        ('ноя', 'ноябрь', 'ноября'),
        ('дек', 'декабрь', 'декабря')
    ]

    PERTAIN = [
        'of',  
        'из'
    ]

    TZOFFSET = {
        'мск': 3 * 3600,
        'msk': 3 * 3600
    }

    UTCZONE = [
        'UTC', 'GMT', 'Z', 'z',
        'utc', 'gmt',
        'мск'
    ]

    WEEKDAYS = [
        ('пн', 'понедельник'),
        ('вт', 'вторник'),
        ('ср', 'среда'),
        ('чт', 'четверг'),
        ('пт', 'пятница'),
        ('сб', 'суббота'),
        ('вс', 'воскресенье')
    ]

#получить юзера
async def get_user(
        tg_id: int
) -> Users: 
    async with Session() as session:
        user = await session.execute(
            select(Users).where(Users.tg_id==tg_id).options(selectinload(Users.reminders))
        )
        user = user.scalar_one_or_none()
        return user

#создать юзера
async def create_user(
        tg_id: int,
        timezone: str = "Europe/Moscow"
) -> Users:
    async with Session() as session:
        user = await get_user(tg_id)
        if user:
            return user
        user = Users(
            tg_id=tg_id,
            timezone=timezone
        )
        session.add(user)
        await session.commit()
        print(f"\nUser {tg_id} was created!\n")
        return user


#адаптировать под русский
#отпарсить дату
async def parse_date(
        message: Message,
        raw_str: str,
):
    try:
        date = parser.parse(raw_str, dayfirst=True, parserinfo=ru_parserinfo(dayfirst=True))
    except parser.ParserError:
        await message.answer("Дата некорректна, попробуйте данный формат:\nЧас/Минута День.Месяц")
        return None
    
    return date

#добавить уведомление
async def add_date_reminder(
        tg_id: int,
        text: str,
        local_date: datetime,
        *,
        trigger: str = "date"
) -> Reminders:
    async with Session() as session:
        user = await get_user(tg_id)
        timezone = user.timezone
        local_date = local_date.replace(tzinfo=ZoneInfo(timezone))
        utc_date = local_date.astimezone(ZoneInfo("UTC"))
        
        reminder = Reminders(
            user_id=user.id,
            text=text,
            remind_at=utc_date
        )

        session.add(reminder)
        await session.commit()

        scheduler.add_job(
            remind,
            trigger=trigger,
            run_date=utc_date,
            args=[reminder.id]
        )

        print(f"\n[green]Reminder {reminder.id} at {reminder.remind_at} was scheduled![/green]\n")
        return reminder
    
#удалить напоминание
async def remove_reminder(
        reminder_id: int
) -> None:
    async with Session() as session:
        await session.execute(delete(Reminders).where(Reminders.id==reminder_id))
        await session.commit()
        print(f"\n[green]Reminder {reminder_id} was deleted[/green]\n")
    
#уведомление
async def remind(
        reminder_id: int
) -> None:
    print(f"\n[green]Reminder {reminder_id} was started![/green]\n")
    async with Session() as session:
        reminder = await session.execute(select(Reminders).where(Reminders.id==reminder_id).options(selectinload(Reminders.user)))
        reminder = reminder.scalar_one()
        await bot.send_message(
            chat_id=reminder.user.tg_id,
            text=reminder.text
        )
        print(f"\n[green]Reminder {reminder.id} at {reminder.remind_at} was completed![/green]\n")
        await remove_reminder(reminder_id)

#отправить прошлые ремайндеры
async def due_remind():
    pass

#ПРОВЕРКИ!!!ОБРАБОТКА ОШИБОК!!!
    
#запуск scheduler
async def start_scheduler() -> AsyncIOScheduler:
    scheduler.start()
    async with Session() as session:
        """
        due_reminders = await session.execute(select(Reminders).where(Reminders.remind_at<=datetime.now(timezone.utc)))
        due_reminders = due_reminders.scalars().all()
        for reminder in due_reminders:
            remind(reminder)
        """

        await session.execute(delete(Reminders).where(Reminders.remind_at<=datetime.now(timezone.utc)))
        await session.commit()
        

        actual_reminders = await session.execute(select(Reminders).options(selectinload(Reminders.user)))
        actual_reminders = actual_reminders.scalars().all()
        for reminder in actual_reminders:
            scheduler.add_job(
                remind,
                trigger=reminder.trigger,
                run_date=reminder.remind_at,
                args=[reminder.id]
            )
        print("\n[green]Scheduler was set up![/green]\n")
        return scheduler
    
