from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message, TelegramObject, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram import Router, BaseMiddleware, F

from services import get_user, create_user, parse_date, add_date_reminder

from typing import Callable, Awaitable, Dict, Any

from models import Users

from datetime import datetime, timedelta

from zoneinfo import ZoneInfo

from rich import print


#проверка и передача пользователя
class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ):
        if isinstance(event, Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
            user = await get_user(event.from_user.id)
            if not user:
                await event.answer("Вы не зарегистрированы. Используйте команду /start")
            data["user"] = user

        elif isinstance(event, CallbackQuery):
            user = await get_user(event.from_user.id)
            if not user:
                await event.answer("Вы не зарегистрированы. Используйте команду /start")
            data["user"] = user
        
        return await handler(event, data)

router = Router()
router.message.middleware(UserMiddleware())
router.callback_query.middleware(UserMiddleware())


#клавиатура start
start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Профиль",callback_data="profile"),
        InlineKeyboardButton(text="Мои напоминания", callback_data="reminders"),
        InlineKeyboardButton(text="Поставить напоминание", callback_data="remind:set")
    ]
])
#клавиатура возврата в меню
return_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Вернуться в меню", callback_data="back:menu")
    ]
])
#клавиатура времени
set_date_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="5 минут", callback_data="remind:time:5"),
        InlineKeyboardButton(text="10 минут", callback_data="remind:time:10"),
        InlineKeyboardButton(text="15 минут", callback_data="remind:time:30"),
        InlineKeyboardButton(text="Час", callback_data="remind:time:60"),
        InlineKeyboardButton(text="Полтора часа", callback_data="remind:time:90"),
        InlineKeyboardButton(text="2 часа", callback_data="remind:time:120")
    ]
])
#без текста
no_text_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Нет", callback_data="remind:text:no")
    ]
])

#состояние set_remind
class RemindStates(StatesGroup):
    waiting_date = State()
    waiting_text = State()


@router.message(Command("start"))
async def start_handler(
    message: Message
):
    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.id)
    
    await message.answer(f"Привет, {message.from_user.first_name}!", reply_markup=start_kb)

#вернуться кнопка
@router.callback_query(F.data == "back:menu")
async def return_handler(
    callback : CallbackQuery,
):
    await callback.message.edit_text(f"Привет, {callback.from_user.first_name}!")
    await callback.message.edit_reply_markup(reply_markup=start_kb)
    await callback.answer()

#профиль
@router.callback_query(F.data == "profile")
async def profile_handler(
    callback: CallbackQuery,
    user: Users
):
    name = callback.from_user.first_name
    register_date = user.created_at.astimezone(ZoneInfo(user.timezone))
    id = user.id
    await callback.message.edit_text(f"<b>Имя:</b>{name}\n<b>Дата регистрации:</b>{register_date.strftime("%d.%m.%Y %H:%M")}\n<b>ID:</b>{id}", parse_mode=ParseMode.HTML)
    await callback.message.edit_reply_markup(reply_markup=return_kb)
    await callback.answer()
    
#список напоминаний
@router.callback_query(F.data == "reminders")
async def reminders_handler(
    callback: CallbackQuery,
    user: Users
):
    text = "<b>Ваши напоминания:</b>\n"
    text = text + '\n'.join([f"{i.remind_at.astimezone(ZoneInfo(user.timezone)).strftime("%d.%m %H:%M")} <b>Текст:</b> {i.text}" for i in user.reminders])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.message.edit_reply_markup(reply_markup=return_kb)
    await callback.answer()

#быстрые уведомления
@router.callback_query(F.data == "remind:set")
async def inline_remind_handler(
    callback: CallbackQuery,
    user: Users
):
    await callback.message.edit_text("Выберите время уведомления")
    await callback.message.edit_reply_markup(reply_markup=set_date_kb)
    await callback.answer()

@router.callback_query(F.data.startswith("remind:time:"))
async def inline_set_remind_handler(
    callback: CallbackQuery,
    user: Users
):
    delta = int(callback.data.split(":")[2])
    date = datetime.now(ZoneInfo(user.timezone)) + timedelta(minutes=delta)
    await add_date_reminder(user.tg_id, "Уведомление!", date)
    await callback.message.edit_text(f"Успешно! Уведомление на {date.strftime('%d.%m %H:%M')}")
    await callback.answer()


#поставить уведомление команда
@router.message(Command("remind"))
async def remind_handler(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    user: Users
):
    if not command.args:
        await message.answer("Напишите время уведомления в удобном для вас формате")
        await state.set_state(RemindStates.waiting_date)
        return
    
    date = await parse_date(message, command.args)
    if date is None:
        await state.set_state(RemindStates.waiting_date)
        return
    
    await state.set_state(RemindStates.waiting_date)
    await state.update_data(waiting_date=date)
    await message.answer("Напишите текст уведомления, или напишите <b>Нет</b> для продолжения", parse_mode=ParseMode.HTML)
    await state.set_state(RemindStates.waiting_text)

#поставить уведомление, ожидание даты
@router.message(RemindStates.waiting_date)
async def process_date(
    message: Message,
    state: FSMContext,
    user: Users
):
    date = await parse_date(message, message.text) 
    if date is None:
        return
    
    await state.update_data(waiting_date=date)
    await message.answer("Напишите текст уведомления, или напишите <b>Нет</b> для продолжения", parse_mode=ParseMode.HTML)
    await state.set_state(RemindStates.waiting_text)
    
#поставить текст к уведомлению
@router.message(RemindStates.waiting_text)
async def process_text(
    message: Message,
    state: FSMContext,
    user: Users
):
    data = await state.get_data()
    date = data["waiting_date"]

    text = message.text
    if text.strip().casefold() == "no" or text.strip().casefold() == "нет":
        text = 'Уведомление!'
    
    reminder = await add_date_reminder(user.tg_id,text,date)

    await message.answer(f"Успешно! Уведомление на {date.strftime('%d.%m %H:%M')}\nТекст:{reminder.text}")
    await state.clear()