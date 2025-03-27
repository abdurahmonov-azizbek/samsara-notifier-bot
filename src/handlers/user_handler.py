import logging as logger

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from src import keyboards, constants
from src.api.api import SamsaraClient
from src.base import bot
from src.models import Notification
from src.services import user_service, company_service, notification_service, truck_service
from src.services.truck_service import get_by_company_id

router = Router()
ITEMS_PER_PAGE = 10


class TruckStatusStates(StatesGroup):
    select_company = State()
    select_truck = State()


async def create_paginated_keyboard(items: list, item_type: str, page: int = 0,
                                    prefix: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min((page + 1) * ITEMS_PER_PAGE, len(items))

    for item in items[start_idx:end_idx]:
        text = f"{item.name}"
        builder.button(text=text, callback_data=f"{prefix}{item_type}_{item.id}")
    if item_type == "company":

        builder.adjust(1)
    else:
        builder.adjust(2)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{prefix}page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{prefix}page_{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel")
    )
    return builder.as_markup()


async def create_paginated_keyboard_with_multiple_selection(items, item_type, page, prefix, selected_ids=None):
    if selected_ids is None:
        selected_ids = []

    items_per_page = 10
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, len(items))

    keyboard = []
    current_row = []
    items_in_row = 2

    for i, item in enumerate(items[start:end]):
        item_id = item.truck_id
        text = f"✅ {item.name}" if item_id in selected_ids else item.name
        button = InlineKeyboardButton(text=text, callback_data=f"{prefix}{item_type}_{item_id}")
        current_row.append(button)

        if len(current_row) == items_in_row or i == len(items[start:end]) - 1:
            keyboard.append(current_row)
            current_row = []

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"{prefix}page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"{prefix}page_{page + 1}"))

    all_selected = all(item.truck_id in selected_ids for item in items)
    select_all_text = "Deselect All" if all_selected else "Select All"
    nav_row.append(InlineKeyboardButton(text=select_all_text, callback_data=f"{prefix}select_all"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(text="✅ Done", callback_data=f"{prefix}done"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"{prefix}cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == "🔎 Provide currently status")
async def provide_status(message: types.Message, state: FSMContext, bot: Bot):
    try:
        telegram_id = message.from_user.id
        user = await user_service.get_by_id(telegram_id, id_column="telegram_id")
        if not user or not user.company_id:
            await message.answer("You’re not linked to any companies.")
            return

        companies = await company_service.get_by_ids(user.company_id)
        if not companies:
            await message.answer("No companies found for your account.")
            return

        if len(companies) == 1:
            await state.update_data(
                telegram_id=telegram_id,
                selected_company_id=companies[0].id,
                api_key=companies[0].api_key
            )
            await show_trucks_for_single_company(message, state, bot)
        else:
            await state.update_data(telegram_id=telegram_id, companies=companies, page=0)
            keyboard = await create_paginated_keyboard(companies, "company", page=0, prefix="comp_")
            await state.set_state(TruckStatusStates.select_company)
            await message.answer("Select a company:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in provide_status: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def show_trucks_for_single_company(message: types.Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0)
        keyboard = await create_paginated_keyboard(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(TruckStatusStates.select_truck)
        await message.answer("Select a truck (or type its name):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_single_company: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.callback_query(TruckStatusStates.select_company)
async def process_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = data["companies"]
        current_page = data.get("page", 0)

        if callback.data.startswith("comp_company_"):
            company_id = int(callback.data.split("_")[2])
            company = next((c for c in companies if c.id == company_id), None)
            if not company or not company.api_key:
                await callback.message.answer("API key not found for this company.")
                return
            await state.update_data(selected_company_id=company_id, api_key=company.api_key)
            await show_trucks(callback, state)
            await callback.message.delete()

        elif callback.data.startswith("comp_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard(companies, "company", new_page, prefix="comp_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "comp_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.cancel_button)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


async def show_trucks(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await callback.message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0)
        keyboard = await create_paginated_keyboard(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(TruckStatusStates.select_truck)
        await callback.message.answer("Select a truck (or type its name):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(TruckStatusStates.select_truck)
async def process_truck_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        trucks = data["trucks"]
        current_page = data.get("page", 0)

        if callback.data.startswith("truck_truck_"):
            truck_id = int(callback.data.split("_")[2])
            selected_truck = next((t for t in trucks if t.id == truck_id), None)
            if not selected_truck:
                await callback.message.answer("Truck not found.")
                return
            await callback.message.answer("Fetching status...")

            await fetch_truck_details(bot, callback.message.chat.id, selected_truck.truck_id, data["api_key"])
            await state.clear()
            await callback.message.delete()

        elif callback.data.startswith("truck_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard(trucks, "truck", new_page, prefix="truck_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.user_menu)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_truck_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.message(TruckStatusStates.select_truck)
async def process_truck_name_input(message: types.Message, state: FSMContext, bot: Bot):
    try:
        truck_name = message.text.strip()
        data = await state.get_data()
        trucks = data["trucks"]

        selected_truck = next((t for t in trucks if t.name.lower() == truck_name.lower()), None)
        if not selected_truck:
            await message.answer("Truck not found. Try again or select from the list.")
            return
        await message.answer("Fetching status...")

        await fetch_truck_details(bot, message.chat.id, selected_truck.truck_id, data["api_key"])

        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_truck_name_input: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def fetch_truck_details(bot: Bot, chat_id: int, truck_id: int, api_key: str):
    try:
        api = SamsaraClient(api_token=api_key)
        vehicle_data = await api.get_truck_details(truck_id)

        details = {
            "truck_id": vehicle_data.get("truck_id", truck_id),
            "unit_name": vehicle_data.get("unit_name", "Unknown"),
            "driver_name": vehicle_data.get("driver_name", "Unknown"),
            "fuel_percent": f"{vehicle_data.get('fuel_percent', 'Unknown')}%",
            "coordinates": vehicle_data.get("coordinates", "Unknown"),
            "speed": vehicle_data.get("speed", "Unknown"),
            "engine_state": vehicle_data.get("engine_state", "Unknown"),
            "time": vehicle_data.get("time", "Unknown"),
            "location": vehicle_data.get("location", "Unknown"),
            "route": vehicle_data.get("route", "Unknown"),
            "remaining_distance": vehicle_data.get("remaining_distance", "Unknown"),
            "eta": vehicle_data.get("eta", "Unknown")
        }

        time_str = details["time"]
        if isinstance(time_str, str):
            time_str = time_str.replace("T", " ").split(".")[0]

        eta_str = details["eta"]
        if isinstance(eta_str, str):
            eta_str = eta_str.replace("T", " ").split(".")[0]
        engine_state = details["engine_state"]
        if engine_state == "Running" or engine_state == "On":
            engine_display = f"{engine_state} 🟢"
        elif engine_state == "Stopped":
            engine_display = f"{engine_state} 🔴"
        elif engine_state == "Off":
            engine_display = f"{engine_state} ⚫️"
        elif engine_state == "Idle":
            engine_display = f"{engine_state} 🟡"
        else:
            engine_display = f"{engine_state}"

        response = (
            f"🚛 *Truck Details* 🚛\n"
            # f"🆔 *ID*: **{details['truck_id']}**\n"
            f"🏷️ *Unit*: **{details['unit_name']}**\n"
            f"👤 *Driver*: **{details['driver_name']}**\n"
            f"⛽️ Fuel: {details['fuel_percent']}\n"
            f"📍 Coordinates: {details['coordinates']}\n"
            f"🚀 Speed: {details['speed']} MPH\n"
            f"⚙️ Engine: {engine_display}\n"
            f"⏰ Time: {time_str}\n"
            f"🌍 Location: {details['location']}\n"
            f"🛤️ Route: {details['route']}\n"
            f"📏 Distance Left: {details['remaining_distance']} mi\n"
            f"🕒 ETA: {eta_str}"
        )
        await bot.send_message(chat_id, response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error fetching truck details: {e}")
        await bot.send_message(chat_id, constants.ERROR_MESSAGE)


class AddAutoNotificationStates(StatesGroup):
    select_company = State()
    select_truck = State()
    time_in_minutes = State()


@router.message(F.text == "⏳ Add auto notification")
async def add_auto_notification(message: types.Message, state: FSMContext, bot: Bot):
    try:
        telegram_id = message.from_user.id
        user = await user_service.get_by_id(telegram_id, id_column="telegram_id")
        if not user or not user.company_id:
            await message.answer("You’re not linked to any companies.")
            return

        companies = await company_service.get_by_ids(user.company_id)
        if not companies:
            await message.answer("No companies found for your account.")
            return

        if len(companies) == 1:
            await state.update_data(
                telegram_id=telegram_id,
                selected_company_id=companies[0].id,
                api_key=companies[0].api_key
            )
            await show_trucks_for_auto_notification_single(message, state, bot)
        else:
            await state.update_data(telegram_id=telegram_id, companies=companies, page=0)
            keyboard = await create_paginated_keyboard(companies, "company", 0, prefix="comp_")
            await state.set_state(AddAutoNotificationStates.select_company)
            await message.answer("Select a company:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in add_auto_notification: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def show_trucks_for_auto_notification_single(message: types.Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddAutoNotificationStates.select_truck)
        await message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_auto_notification_single: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def show_trucks_for_auto_notification(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await callback.message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddAutoNotificationStates.select_truck)
        await callback.message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddAutoNotificationStates.select_company)
async def process_auto_notif_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = data["companies"]
        current_page = data.get("page", 0)

        if callback.data.startswith("comp_company_"):
            company_id = int(callback.data.split("_")[2])
            company = next((c for c in companies if c.id == company_id), None)
            if not company or not company.api_key:
                await callback.message.answer("API key not found for this company.")
                return
            await state.update_data(selected_company_id=company_id, api_key=company.api_key)
            await show_trucks_for_auto_notification(callback, state)
            await callback.message.delete()

        elif callback.data.startswith("comp_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard(companies, "company", new_page, prefix="comp_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "comp_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.cancel_button)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddAutoNotificationStates.select_truck)
async def process_auto_notif_truck_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        trucks = data["trucks"]
        selected_truck_ids = data.get("selected_truck_ids", [])

        if callback.data.startswith("truck_truck_"):
            truck_id = int(callback.data.split("_")[2])
            selected_truck = next((t for t in trucks if t.truck_id == truck_id), None)
            if not selected_truck:
                await callback.message.answer("Truck not found.")
                return

            if truck_id in selected_truck_ids:
                selected_truck_ids.remove(truck_id)
            else:
                selected_truck_ids.append(truck_id)

            await state.update_data(selected_truck_ids=selected_truck_ids)

            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("truck_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", new_page, prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_select_all":
            all_truck_ids = [truck.truck_id for truck in trucks]
            if set(selected_truck_ids) == set(all_truck_ids):
                selected_truck_ids.clear()
            else:
                selected_truck_ids = all_truck_ids[:]

            await state.update_data(selected_truck_ids=selected_truck_ids)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_done" and selected_truck_ids:
            await state.set_state(AddAutoNotificationStates.time_in_minutes)
            times_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ 60 minutes (1 hour)", callback_data="times_60")],
                [InlineKeyboardButton(text="⏳ 120 minutes (2 hours)", callback_data="times_120")],
                [InlineKeyboardButton(text="⏳ 180 minutes (3 hours)", callback_data="times_180")],
                [InlineKeyboardButton(text="⏳ 240 minutes (4 hours)", callback_data="times_240")],
                [InlineKeyboardButton(text="⏳ 300 minutes (5 hours)", callback_data="times_300")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ])
            await callback.message.edit_text(
                f"Selected {len(selected_truck_ids)} truck(s). Choose notification time or enter your own:",
                reply_markup=times_markup
            )

        elif callback.data == "truck_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.user_menu)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_truck_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


async def save_notification(telegram_id, truck_ids, time_in_minutes, bot: Bot, state: FSMContext):
    try:
        for truck_id in truck_ids:
            notification = Notification(
                id=None,
                telegram_id=telegram_id,
                truck_id=truck_id,
                notification_type_id=None,
                every_minutes=time_in_minutes,
                last_send_time=None,
                warning_type=None,
                engine_status=None
            )
            await notification_service.create_auto_notification(notification)
    except Exception as e:
        await state.clear()
        logger.error(f"Error while saving notification: {e}")
        await bot.send_message(telegram_id, constants.ERROR_MESSAGE)


@router.callback_query(AddAutoNotificationStates.time_in_minutes)
async def process_auto_notif_time(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        if not callback.data.startswith("times_"):
            return

        time = int(callback.data.split("_")[-1])
        data = await state.get_data()
        selected_truck_ids = data["selected_truck_ids"]
        await state.clear()

        await save_notification(data["telegram_id"], selected_truck_ids, time, bot=bot, state=state)
        await callback.message.answer(
            f"Notifications added for {len(selected_truck_ids)} truck(s) ✅",
            reply_markup=keyboards.user_menu
        )
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in process_auto_notif_time: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)


@router.message(AddAutoNotificationStates.time_in_minutes)
async def process_auto_notif_time_b(message: types.Message, state: FSMContext):
    try:
        time = message.text.strip()
        if not time.isdigit():
            await message.answer("Please enter correct time (in minutes): ", reply_markup=keyboards.cancel_button)
            return

        data = await state.get_data()
        selected_truck_ids = data["selected_truck_ids"]
        await state.clear()

        await save_notification(data["telegram_id"], selected_truck_ids, int(time), bot=bot, state=state)
        await message.answer(f"Notifications added for {len(selected_truck_ids)} truck(s) ✅",
                             reply_markup=keyboards.user_menu)
    except Exception as e:
        logger.error(f"Error in process_auto_notif_time: {e}")
        await message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)


class AddStatusNotificationStates(StatesGroup):
    select_company = State()
    select_truck = State()
    status = State()


async def show_trucks_for_status_notification_single(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddStatusNotificationStates.select_truck)
        await message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_status_notification_single: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(F.text == "➕ Add status notification")
async def add_status_notification(message: types.Message, state: FSMContext, bot: Bot):
    try:
        telegram_id = message.from_user.id
        user = await user_service.get_by_id(telegram_id, id_column="telegram_id")
        if not user or not user.company_id:
            await message.answer("You’re not linked to any companies.")
            return

        companies = await company_service.get_by_ids(user.company_id)
        if not companies:
            await message.answer("No companies found for your account.")
            return

        if len(companies) == 1:
            await state.update_data(
                telegram_id=telegram_id,
                selected_company_id=companies[0].id,
                api_key=companies[0].api_key
            )
            await show_trucks_for_status_notification_single(message, state)
        else:
            await state.update_data(telegram_id=telegram_id, companies=companies, page=0)
            keyboard = await create_paginated_keyboard(companies, "company", 0, prefix="comp_")
            await state.set_state(AddStatusNotificationStates.select_company)
            await message.answer("Select a company:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in add_status_notification: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def show_trucks_for_status_notification(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await callback.message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddStatusNotificationStates.select_truck)
        await callback.message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_status_notification: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddStatusNotificationStates.select_company)
async def process_status_notif_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = data["companies"]
        current_page = data.get("page", 0)

        if callback.data.startswith("comp_company_"):
            company_id = int(callback.data.split("_")[2])
            company = next((c for c in companies if c.id == company_id), None)
            if not company or not company.api_key:
                await callback.message.answer("API key not found for this company.")
                return
            await state.update_data(selected_company_id=company_id, api_key=company.api_key)
            await show_trucks_for_status_notification(callback, state)
            await callback.message.delete()

        elif callback.data.startswith("comp_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard(companies, "company", new_page, prefix="comp_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "comp_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.cancel_button)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_status_notif_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddStatusNotificationStates.select_truck)
async def process_status_notif_truck_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        trucks = data["trucks"]
        selected_truck_ids = data.get("selected_truck_ids", [])

        if callback.data.startswith("truck_truck_"):
            truck_id = int(callback.data.split("_")[2])
            selected_truck = next((t for t in trucks if t.truck_id == truck_id), None)
            if not selected_truck:
                await callback.message.answer("Truck not found.")
                return

            if truck_id in selected_truck_ids:
                selected_truck_ids.remove(truck_id)
            else:
                selected_truck_ids.append(truck_id)

            await state.update_data(selected_truck_ids=selected_truck_ids)

            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("truck_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", new_page, prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_select_all":
            all_truck_ids = [truck.truck_id for truck in trucks]
            if set(selected_truck_ids) == set(all_truck_ids):
                selected_truck_ids.clear()
            else:
                selected_truck_ids = all_truck_ids[:]

            await state.update_data(selected_truck_ids=selected_truck_ids)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_done" and selected_truck_ids:
            await state.set_state(AddStatusNotificationStates.status)
            status_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Device Movement", callback_data="status_deviceMovement")],
                [InlineKeyboardButton(text="🔴 Device Movement Stopped", callback_data="status_deviceMovementStopped")],
                # [InlineKeyboardButton(text="⚫️ Off", callback_data="status_off")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ])
            await callback.message.edit_text(
                f"Selected {len(selected_truck_ids)} truck(s). Choose engine status:",
                reply_markup=status_markup
            )

        elif callback.data == "truck_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.user_menu)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_status_notif_truck_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


async def save_status_notification(telegram_id, truck_ids, engine_status):
    try:
        for truck_id in truck_ids:
            notification = Notification(
                id=None,
                telegram_id=telegram_id,
                truck_id=truck_id,
                notification_type_id=2,
                every_minutes=None,
                last_send_time=None,
                warning_type=None,
                engine_status=engine_status
            )
            await notification_service.create_status_notification(notification)
        return True
    except Exception as e:
        logger.error(f"Error while saving status notification: {e}")
        return False


@router.callback_query(AddStatusNotificationStates.status)
async def finish_status_notification(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        if not callback.data.startswith("status_"):
            return

        engine_status = callback.data.strip().split("_")[-1]
        data = await state.get_data()
        selected_truck_ids = data["selected_truck_ids"]
        await state.clear()

        if await save_status_notification(data["telegram_id"], selected_truck_ids, engine_status):
            await callback.message.answer(
                f"Notifications added for {len(selected_truck_ids)} truck(s) ✅",
                reply_markup=keyboards.user_menu
            )
        else:
            await callback.message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)

        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in finish_status_notification: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)


class AddWarningNotificationStates(StatesGroup):
    select_company = State()
    select_truck = State()
    warning = State()


async def show_trucks_for_warning_notification_single(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddWarningNotificationStates.select_truck)
        await message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_warning_notification_single: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(F.text == "⚠️ Add warning notification")
async def add_warning_notification(message: types.Message, state: FSMContext, bot: Bot):
    try:
        telegram_id = message.from_user.id
        user = await user_service.get_by_id(telegram_id, id_column="telegram_id")
        if not user or not user.company_id:
            await message.answer("You’re not linked to any companies.")
            return

        companies = await company_service.get_by_ids(user.company_id)
        if not companies:
            await message.answer("No companies found for your account.")
            return

        if len(companies) == 1:
            await state.update_data(
                telegram_id=telegram_id,
                selected_company_id=companies[0].id,
                api_key=companies[0].api_key
            )
            await show_trucks_for_warning_notification_single(message, state)
        else:
            await state.update_data(telegram_id=telegram_id, companies=companies, page=0)
            keyboard = await create_paginated_keyboard(companies, "company", 0, prefix="comp_")
            await state.set_state(AddWarningNotificationStates.select_company)
            await message.answer("Select a company:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in add_warning_notification: {e}")
        await message.answer(constants.ERROR_MESSAGE)


async def show_trucks_for_warning_notification(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        company_id = data["selected_company_id"]
        trucks = await get_by_company_id(company_id)
        if not trucks:
            await callback.message.answer("No trucks found for this company.")
            return

        await state.update_data(trucks=trucks, page=0, selected_truck_ids=[])
        keyboard = await create_paginated_keyboard_with_multiple_selection(trucks, "truck", page=0, prefix="truck_")
        await state.set_state(AddWarningNotificationStates.select_truck)
        await callback.message.answer("Select one or more trucks (tap to toggle):", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_trucks_for_warning_notification: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddWarningNotificationStates.select_company)
async def process_warning_notif_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = data["companies"]
        current_page = data.get("page", 0)

        if callback.data.startswith("comp_company_"):
            company_id = int(callback.data.split("_")[2])
            company = next((c for c in companies if c.id == company_id), None)
            if not company or not company.api_key:
                await callback.message.answer("API key not found for this company.")
                return
            await state.update_data(selected_company_id=company_id, api_key=company.api_key)
            await show_trucks_for_warning_notification(callback, state)
            await callback.message.delete()

        elif callback.data.startswith("comp_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard(companies, "company", new_page, prefix="comp_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "comp_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.cancel_button)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_warning_notif_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddWarningNotificationStates.select_truck)
async def process_warning_notif_truck_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        trucks = data["trucks"]
        selected_truck_ids = data.get("selected_truck_ids", [])

        if callback.data.startswith("truck_truck_"):
            truck_id = int(callback.data.split("_")[2])
            selected_truck = next((t for t in trucks if t.truck_id == truck_id), None)
            if not selected_truck:
                await callback.message.answer("Truck not found.")
                return

            if truck_id in selected_truck_ids:
                selected_truck_ids.remove(truck_id)
            else:
                selected_truck_ids.append(truck_id)

            await state.update_data(selected_truck_ids=selected_truck_ids)

            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("truck_page_"):
            new_page = int(callback.data.split("_")[2])
            await state.update_data(page=new_page)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", new_page, prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_select_all":
            all_truck_ids = [truck.truck_id for truck in trucks]
            if set(selected_truck_ids) == set(all_truck_ids):
                selected_truck_ids.clear()
            else:
                selected_truck_ids = all_truck_ids[:]

            await state.update_data(selected_truck_ids=selected_truck_ids)
            keyboard = await create_paginated_keyboard_with_multiple_selection(
                trucks, "truck", data["page"], prefix="truck_", selected_ids=selected_truck_ids
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "truck_done" and selected_truck_ids:
            await state.set_state(AddWarningNotificationStates.warning)
            warning_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="SevereSpeedingEnded", callback_data="warning_SevereSpeedingEnded")],
                [InlineKeyboardButton(text="SevereSpeedingStarted", callback_data="warning_SevereSpeedingStarted")],
                [InlineKeyboardButton(text="PredictiveMaintenanceAlert",
                                      callback_data="warning_PredictiveMaintenanceAlert")],
                [InlineKeyboardButton(text="SuddenFuelLevelDrop", callback_data="warning_SuddenFuelLevelDrop")],
                [InlineKeyboardButton(text="SuddenFuelLevelRise", callback_data="warning_SuddenFuelLevelRise")],
                [InlineKeyboardButton(text="GatewayUnplugged", callback_data="warning_GatewayUnplugged")],
                [InlineKeyboardButton(text="HarshEvent", callback_data="warning_harshEvent")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ])
            warning_descriptions = (
                f"Selected {len(selected_truck_ids)} truck(s). Choose warning type:\n\n"
                f"1. *SevereSpeedingEnded*: Indicates that a period of severe speeding has ended. The vehicle is now within normal speed limits.\n"
                f"2. *SevereSpeedingStarted*: Alerts that the vehicle has begun severely exceeding the speed limit, posing a safety risk.\n"
                f"3. *PredictiveMaintenanceAlert*: Warns that the vehicle may need maintenance soon based on predictive data to prevent breakdowns.\n"
                f"4. *SuddenFuelLevelDrop*: Notifies a rapid, unexpected decrease in fuel level, possibly indicating a leak or malfunction.\n"
                f"5. *SuddenFuelLevelRise*: Signals an unusual sudden increase in fuel level, possibly due to refueling or a sensor error.\n"
                f"6. *GatewayUnplugged*: Warns that the vehicle's tracking or diagnostic gateway device has been disconnected.\n"
                f"7. *HarshEvent*: Indicates a harsh driving event like sudden braking or sharp acceleration, affecting safety or condition."
            )

            await callback.message.edit_text(
                warning_descriptions,
                reply_markup=warning_markup,
                parse_mode="Markdown"
            )

        elif callback.data == "truck_cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.user_menu)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_warning_notif_truck_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


async def save_warning_notification(telegram_id, truck_ids, warning):
    try:
        for truck_id in truck_ids:
            notification = Notification(
                id=None,
                telegram_id=telegram_id,
                truck_id=truck_id,
                notification_type_id=1,
                every_minutes=None,
                last_send_time=None,
                warning_type=warning,
                engine_status=None
            )
            await notification_service.create_warning_notification(notification)
        return True
    except Exception as e:
        logger.error(f"Error while saving warning notification: {e}")
        return False


@router.callback_query(AddWarningNotificationStates.warning)
async def finish_warning_notification(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        if not callback.data.startswith("warning_"):
            return

        warning_type = callback.data.strip().split("_")[-1]
        data = await state.get_data()
        selected_truck_ids = data["selected_truck_ids"]
        await state.clear()

        if await save_warning_notification(data["telegram_id"], selected_truck_ids, warning_type):
            await callback.message.answer(
                f"Notifications added for {len(selected_truck_ids)} truck(s) ✅",
                reply_markup=keyboards.user_menu
            )
        else:
            await callback.message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)

        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in finish_warning_notification: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE, reply_markup=keyboards.user_menu)


@router.message(F.text == "🎊 My notifications")
async def show_all_notifications(message: types.Message, state: FSMContext):
    try:
        loading_message = await message.answer("Fetching your all notifications...")
        telegram_id = message.from_user.id
        notifications = await notification_service.get_by_query(
            f"select * from {constants.NOTIFICATION_TABLE} WHERE telegram_id = {telegram_id}")
        if len(notifications) == 0:
            await message.answer("You have no notifications yet!")
            return

        msg = "🎊 Your notifications:\n"
        for notification in notifications:
            if len(msg) > 3000 and len(msg) < 4096:
                await message.answer(msg, parse_mode="Markdown")
                msg = ""

            truck = await truck_service.get_by_id(notification.truck_id, "truck_id")
            if not truck:
                logger.info(f"Truck not found for notification: {notification.id}, truck id: {notification.truck_id}")
                continue

            if notification.notification_type_id == 1:
                msg += f"🏷️ *Unit*: {truck.name}\n"
                msg += f"📍 *Notification type*: Warning ⚠️\n"
                msg += f"⚠️ *Warning*: {notification.warning_type}\n\n"
            elif notification.notification_type_id == 2:
                msg += f"🏷️ *Unit*: {truck.name}\n"
                msg += f"📍 *Notification type*: Engine status ⚙️\n"
                emoji = ""
                engine = str(notification.engine_status).strip().lower()
                if engine == "running":
                    emoji = "🟢"
                elif engine == "stopped":
                    emoji = "🔴"
                elif engine == "off":
                    emoji = "⚫️"
                msg += f"⚙️ *Engine status*: {notification.engine_status} {emoji}\n\n"
            elif notification.notification_type_id == 3:
                msg += f"🏷️ *Unit*: {truck.name}\n"
                msg += f"📍 *Notification type*: Timer ⏳\n"
                msg += f"⏳ *Time*: {notification.every_minutes} minutes\n\n"

        await loading_message.delete()
        await message.answer(msg, parse_mode="Markdown")


    except Exception as e:
        logger.error(f"Error while show all notifications: {e}")


async def create_paginated_keyboard_for_notifications(items: list, item_type: str, page: int = 0,
                                                      prefix: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min((page + 1) * ITEMS_PER_PAGE, len(items))

    for item in items[start_idx:end_idx]:
        truck = await truck_service.get_by_id(item.truck_id, "truck_id")
        if not truck:
            continue

        text = ""
        if item.notification_type_id == 1:
            text = f"🏷️ {truck.name} | Warning ⚠️ | {item.warning_type}"
        elif item.notification_type_id == 2:
            text = f"🏷️ {truck.name} | Status ⚙️ | {item.engine_status}"
        elif item.notification_type_id == 3:
            text = f"🏷️ {truck.name} | Timer ⏳ | {item.every_minutes} minutes"
        else:
            text = "UNKNOWN"

        builder.button(text=text, callback_data=f"{prefix}{item_type}_{item.id}")

    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{prefix}page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{prefix}page_{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel")
    )
    return builder.as_markup()


class DeleteNotificationStates(StatesGroup):
    select_notification = State()


@router.message(F.text == "❌ Delete notification")
async def delete_notification(message: types.Message, state: FSMContext):
    try:
        telegram_id = message.from_user.id
        notifications = await notification_service.get_by_query(
            f"select * from {constants.NOTIFICATION_TABLE} WHERE telegram_id = {telegram_id}")
        if len(notifications) == 0:
            await message.answer("You have no notifications yet!")
            return

        await state.update_data(notifications=notifications)
        await state.set_state(DeleteNotificationStates.select_notification)
        markup = await create_paginated_keyboard_for_notifications(notifications, "notification", 0, "notif_")
        await message.answer("Choose notification you want to delete", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in delete_notification: {e}")


@router.callback_query(DeleteNotificationStates.select_notification)
async def process_delete_notification(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        notifications = data["notifications"]

        if callback.data.startswith("notif_page_"):
            new_page = int(callback.data.split("_")[2])
            keyboard = await create_paginated_keyboard_for_notifications(notifications, "notification", new_page,
                                                                         "notif_")
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("notif_notification_"):
            notification_id = int(callback.data.split("_")[-1])
            await notification_service.delete_by_id(notification_id)
            await callback.message.answer("Notification deleted ✅", reply_markup=keyboards.user_menu)
            await callback.message.delete()
            await state.clear()

    except Exception as e:
        logger.error(f"Error in process_delete_notification: {e}")


class ClearAllNotificationsStates(StatesGroup):
    sure = State()


@router.message(F.text == "🧹 Clear all notifications")
async def clear_all_notifications(message: types.Message, state: FSMContext):
    try:
        await state.set_state(ClearAllNotificationsStates.sure)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Yes I'm sure ✅", callback_data="delete_all")],
            [InlineKeyboardButton(text="No, my bad ❌", callback_data="cancel")]
        ])
        await message.answer("*Do you want to delete all your notifications?* ", parse_mode="Markdown",
                             reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in clear_all_notifications: {e}")


@router.callback_query(ClearAllNotificationsStates.sure)
async def process_delete_all_notifications(callback: CallbackQuery, state: FSMContext):
    try:
        telegram_id = callback.message.chat.id
        if callback.data == "delete_all":
            await notification_service.delete_by_id(telegram_id, "telegram_id")
            await callback.message.answer("Deleted ✅", reply_markup=keyboards.user_menu)
            await callback.message.delete()
            await state.clear()
    except Exception as e:
        logger.error(f"Error in clear_all_notifications: {e}")
