import logging as logger

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from src import keyboards, constants
from src.api.api import SamsaraClient
from src.services import user_service, company_service
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

    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{prefix}page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{prefix}page_{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"{prefix}cancel")
    )
    return builder.as_markup()


@router.message(F.text == "🔎 Provide currently status")
async def provide_status(message: types.Message, state: FSMContext, bot: Bot):  # Added bot parameter
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
            await callback.message.answer("Operation cancelled.", reply_markup=keyboards.cancel_button)

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
