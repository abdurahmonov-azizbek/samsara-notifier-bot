from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import *
from logger import logger
from src.models import Company, User
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src import constants, keyboards
from src.functions import *
from src.services import company_service, user_service
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


class AddCompanyStates(StatesGroup):
    full_name = State()
    api_key = State()


@router.message(F.text == "➕ Add company")
async def add_company(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            logger.warning(f"user [{user_id}] who not admin tried to use admin command!")
            return

        await state.set_state(AddCompanyStates.full_name)
        await message.answer("Enter company's full name: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error("Error in '➕ Add Company'")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(AddCompanyStates.full_name)
async def ask_api_key(message: Message, state: FSMContext):
    try:
        company_name = message.text.strip()
        await state.update_data(full_name=company_name)
        await state.set_state(AddCompanyStates.api_key)
        await message.answer(f"Enter api-key from samsara for <b>{company_name}</b>",
                             reply_markup=keyboards.cancel_button, parse_mode="html")
    except Exception as e:
        logger.error(f"Error in ask_api_key function: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(AddCompanyStates.api_key)
async def save_company(message: Message, state: FSMContext):
    try:
        api_key = message.text.strip()
        await state.update_data(api_key=api_key)
        data = await state.get_data()
        await state.clear()

        company = Company(
            id=None,
            name=data['full_name'],
            api_key=data['api_key']
        )
        await company_service.create(company)
        await message.answer("✅ Company added succesfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error while saving company: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(F.text == "🏢 All companies")
async def show_all_companies(message: Message):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        await message.answer("Wait...")
        companies = await company_service.get_all()
        text = "🏢All companies:\n\n"

        for company in companies:
            text += f"<b>🆔 {company.id}\n</b>"
            text += f"<b>🗣 {company.name}\n</b>"
            text += f"<b>🔑 {company.api_key}\n\n</b>"

        await message.answer(text, parse_mode="html")
    except Exception as e:
        logger.error(f"Error while showing all companies: {e}")
        await message.answer(constants.ERROR_MESSAGE)


class EditCompanyStates(StatesGroup):
    select_company = State()
    select_option = State()
    name = State()
    api_key = State()


@router.message(F.text == "✏️ Edit company")
async def edit_company(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        companies = await company_service.get_all()
        buttons = []
        for company in companies:
            buttons.append([KeyboardButton(text=company.name)])

        buttons.append([KeyboardButton(text="⬅️ Cancel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        await state.set_state(EditCompanyStates.select_company)
        await message.answer("Select company: ", reply_markup=markup)

    except Exception as e:
        logger.error(f"Error while editing company: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(EditCompanyStates.select_company)
async def ask_new_name(message: Message, state: FSMContext):
    try:
        company_name = message.text.strip()
        company = await company_service.get_by_name(company_name)
        if not company:
            await message.answer("Please use buttons!")
            return

        await state.update_data(id=company.id, current_company=company)

        menu = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Change Company Name", callback_data="edit_company_name")],
            [InlineKeyboardButton(text="Change API KEY", callback_data="edit_api_key")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])

        await state.set_state(EditCompanyStates.select_option)
        await message.answer("What would you like to edit ?", reply_markup=menu)

    except Exception as e:
        logger.error(f"Error in ask_new_name: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.callback_query(EditCompanyStates.select_option)
async def process_company_edit(callback: CallbackQuery, state: FSMContext):
    try:
        if callback.data == "edit_company_name":
            await callback.message.edit_text("Enter company name: ", reply_markup=keyboards.cancel_inline)
            await state.set_state(EditCompanyStates.name)
        elif callback.data == "edit_api_key":
            await callback.message.edit_text("Enter new API KEY: ", reply_markup=keyboards.cancel_inline)
            await state.set_state(EditCompanyStates.api_key)

    except Exception as e:
        logger.error(f"Error while editing company: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)

@router.message(EditCompanyStates.name)
async def ask_new_api_key(message: Message, state: FSMContext):
    try:
        name = message.text.strip()
        data = await state.get_data()
        await state.clear()

        company = data["current_company"]
        company.name = name
        await company_service.update(company)
        await message.answer("Company name changed ✅", reply_markup=keyboards.admin_menu)

    except Exception as e:
        logger.error(f"Error in ask_new_api_key: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditCompanyStates.api_key)
async def ask_new_api_key(message: Message, state: FSMContext):
    try:
        api_key = message.text.strip()
        data = await state.get_data()
        await state.clear()

        company = data["current_company"]
        company.api_key = api_key
        await company_service.update(company)
        await message.answer("Company API KEY changed ✅", reply_markup=keyboards.admin_menu)

    except Exception as e:
        logger.error(f"Error in ask_new_api_key: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditCompanyStates.api_key)
async def ask_new_api_key(message: Message, state: FSMContext):
    try:
        await state.update_data(api_key=message.text.strip())
        data = await state.get_data()
        await state.clear()

        company = Company(
            id=data['id'],
            name=data['name'],
            api_key=data['api_key']
        )

        await company_service.update(company)
        await message.answer("✅ Company successfully updated", reply_markup=keyboards.admin_menu)

    except Exception as e:
        logger.error(f"Error in ask_new_api_key: {e}")
        await message.answer(constants.ERROR_MESSAGE)


class DeleteCompanyStates(StatesGroup):
    id = State()


@router.message(F.text == "❌ Delete company")
async def delete_company(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        companies = await company_service.get_all()
        buttons = []
        for company in companies:
            buttons.append([KeyboardButton(text=company.name)])

        buttons.append([KeyboardButton(text="⬅️ Cancel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        await state.set_state(DeleteCompanyStates.id)
        await message.answer("Select company: ", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in delete_company: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(DeleteCompanyStates.id)
async def delete_company_by_id(message: Message, state: FSMContext):
    try:
        company_name = message.text.strip()
        company = await company_service.get_by_name(company_name)
        if not company:
            await message.answer("Please use buttons!")
            return

        await company_service.delete_by_id(company.id)
        await state.clear()
        await message.answer("✅ Company deleted successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error in delete_company_by_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)


class AddUserStates(StatesGroup):
    telegram_id = State()
    full_name = State()
    company_id = State()


@router.message(F.text == "➕ Add user")
async def add_user(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            logger.warning(f"Unauthorized user [{user_id}] tried to use admin command!")
            return

        await state.set_state(AddUserStates.telegram_id)
        await message.answer("Enter user's Telegram ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error("Error in '➕ Add User'")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(AddUserStates.telegram_id)
async def ask_full_name(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
        await state.update_data(telegram_id=telegram_id)
        await state.set_state(AddUserStates.full_name)
        await message.answer("Enter user's full name: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in ask_full_name: {e}")
        await message.answer(constants.ERROR_MESSAGE)


ITEMS_PER_PAGE = 10


async def generate_company_keyboard(companies, selected_ids=None, page=0):
    if selected_ids is None:
        selected_ids = set()

    builder = InlineKeyboardBuilder()
    total_pages = (len(companies) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start_idx = page * ITEMS_PER_PAGE
    end_idx = min((page + 1) * ITEMS_PER_PAGE, len(companies))
    for company in companies[start_idx:end_idx]:
        prefix = "✅ " if company.id in selected_ids else ""
        button_text = f"{prefix}{company.name}"
        builder.button(
            text=button_text,
            callback_data=f"company_{company.id}"
        )

    builder.adjust(2)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="✅ Done", callback_data="done"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    )

    return builder.as_markup()


@router.message(AddUserStates.full_name)
async def ask_company_id(message: types.Message, state: FSMContext):
    try:
        full_name = message.text.strip()
        companies = await company_service.get_all()

        if not companies:
            await message.answer("No companies available.")
            return

        await state.update_data(full_name=full_name, selected_companies=set(), page=0)
        await state.set_state(AddUserStates.company_id)

        keyboard = await generate_company_keyboard(companies)
        await message.answer("Select companies (you can choose multiple):", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in ask_company_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.callback_query(AddUserStates.company_id)
async def process_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = await company_service.get_all()
        selected_companies = set(data.get('selected_companies', set()))
        current_page = data.get('page', 0)

        if callback.data.startswith("company_"):
            company_id = int(callback.data.split("_")[1])
            if company_id in selected_companies:
                selected_companies.remove(company_id)
            else:
                selected_companies.add(company_id)
            await state.update_data(selected_companies=selected_companies)

            keyboard = await generate_company_keyboard(companies, selected_companies, current_page)
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("page_"):
            new_page = int(callback.data.split("_")[1])
            await state.update_data(page=new_page)
            keyboard = await generate_company_keyboard(companies, selected_companies, new_page)
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "done":
            if not selected_companies:
                await callback.answer("Please select at least one company!", show_alert=True)
                return

            await state.update_data(selected_companies=selected_companies)
            await save_users(callback.message, state)
            await callback.message.delete()

        elif callback.data == "cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Cancelled.", reply_markup=keyboards.admin_menu)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


async def save_users(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        selected_companies = data.get('selected_companies', set())

        await state.clear()

        user = User(
            id=None,
            telegram_id=data['telegram_id'],
            full_name=data['full_name'],
            company_id=selected_companies,
            balance=0
        )
        await user_service.create(user)

        await message.answer("✅ Users added successfully", reply_markup=keyboards.admin_menu)

    except Exception as e:
        logger.error(f"Error while saving users: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(F.text == "👥 All users")
async def show_all_users(message: Message):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        await message.answer("Wait...")
        users = await user_service.get_all()
        text = "👥 All users:\n\n"

        for user in users:
            companies = await company_service.get_by_ids(user.company_id)
            text += f"<b>🆔 {user.id}</b>\n"
            text += f"<b>👤 {user.full_name}</b>\n"
            text += f"<b>📱 Telegram ID: {user.telegram_id}</b>\n"
            # text += f"<b>🏢 Company ID: {user.company_id}</b>\n"
            text += f"<b>🏢 Companies: </b>\n"
            counter = 1
            for company in companies:
                text += f"<b>\t{counter}. {company.name}\n</b>"
                counter += 1

        await message.answer(text, parse_mode="html")
    except Exception as e:
        logger.error(f"Error while showing all users: {e}")
        await message.answer(constants.ERROR_MESSAGE)


class EditUserStates(StatesGroup):
    select_user = State()
    select_option = State()
    telegram_id = State()
    full_name = State()
    company_id = State()


@router.message(F.text == "✏️ Edit user")
async def edit_user(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        users = await user_service.get_all()
        if not users:
            await message.answer("No users available.")
            return

        buttons = []
        for user in users:
            buttons.append([KeyboardButton(text=str(user.full_name))])

        buttons.append([KeyboardButton(text="⬅️ Cancel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        await state.set_state(EditUserStates.select_user)
        await message.answer("Select the user to edit: ", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error while editing user: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(EditUserStates.select_user)
async def show_edit_options(message: types.Message, state: FSMContext):
    try:
        user = await user_service.get_by_full_name(message.text.strip())
        if not user:
            await message.answer("Please use buttons!")
            return

        await state.update_data(id=user.id, current_user=user)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Change Telegram ID", callback_data="edit_telegram_id")],
            [InlineKeyboardButton(text="Change Full Name", callback_data="edit_full_name")],
            [InlineKeyboardButton(text="Change Company", callback_data="edit_company_id")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ])

        await state.set_state(EditUserStates.select_option)
        await message.answer("What would you like to edit?", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in show_edit_options: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.callback_query(EditUserStates.select_option)
async def process_edit_option(callback: types.CallbackQuery, state: FSMContext):
    try:
        if callback.data == "edit_telegram_id":
            await state.set_state(EditUserStates.telegram_id)
            await callback.message.edit_text("Enter the new Telegram ID:", reply_markup=keyboards.cancel_inline)

        elif callback.data == "edit_full_name":
            await state.set_state(EditUserStates.full_name)
            await callback.message.edit_text("Enter the new full name:", reply_markup=keyboards.cancel_inline)

        elif callback.data == "edit_company_id":
            companies = await company_service.get_all()
            if not companies:
                await callback.message.edit_text("No companies available.")
                return

            await state.set_state(EditUserStates.company_id)
            await state.update_data(selected_companies=set(), page=0)
            keyboard = await generate_company_keyboard(companies)
            await callback.message.edit_text("Select new companies (multiple selection allowed):",
                                             reply_markup=keyboard)

        elif callback.data == "cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Cancelled.", reply_markup=keyboards.admin_menu)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_edit_option: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


@router.message(EditUserStates.telegram_id)
async def save_new_telegram_id(message: types.Message, state: FSMContext):
    try:
        new_telegram_id = int(message.text.strip())
        if new_telegram_id != "⬅️ Cancel":
            data = await state.get_data()
            user = data['current_user']

            updated_user = User(
                id=user.id,
                telegram_id=new_telegram_id,
                full_name=user.full_name,
                company_id=user.company_id,
                balance=user.balance
            )
            await user_service.update(updated_user)

            await state.clear()
            await message.answer("✅ Telegram ID updated successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error in save_new_telegram_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(EditUserStates.full_name)
async def save_new_full_name(message: types.Message, state: FSMContext):
    try:
        new_full_name = message.text.strip()
        if new_full_name != "⬅️ Cancel":
            data = await state.get_data()
            user = data['current_user']

            updated_user = User(
                id=user.id,
                telegram_id=user.telegram_id,
                full_name=new_full_name,
                company_id=user.company_id,
                balance=user.balance
            )
            await user_service.update(updated_user)

            await state.clear()
            await message.answer("✅ Full name updated successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error in save_new_full_name: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.callback_query(EditUserStates.company_id)
async def process_company_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        companies = await company_service.get_all()
        selected_companies = set(data.get('selected_companies', set()))
        current_page = data.get('page', 0)

        if callback.data.startswith("company_"):
            company_id = int(callback.data.split("_")[1])
            if company_id in selected_companies:
                selected_companies.remove(company_id)
            else:
                selected_companies.add(company_id)
            await state.update_data(selected_companies=selected_companies)

            keyboard = await generate_company_keyboard(companies, selected_companies, current_page)
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data.startswith("page_"):
            new_page = int(callback.data.split("_")[1])
            await state.update_data(page=new_page)
            keyboard = await generate_company_keyboard(companies, selected_companies, new_page)
            await callback.message.edit_reply_markup(reply_markup=keyboard)

        elif callback.data == "done":
            if not selected_companies:
                await callback.answer("Please select at least one company!", show_alert=True)
                return
            user = data['current_user']
            updated_user = User(
                id=user.id,
                telegram_id=user.telegram_id,
                full_name=user.full_name,
                company_id=list(selected_companies),  # Convert set to list for array
                balance=user.balance
            )
            await user_service.update(updated_user)
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("✅ Companies updated successfully", reply_markup=keyboards.admin_menu)

        elif callback.data == "cancel":
            await state.clear()
            await callback.message.delete()
            await callback.message.answer("Cancelled.", reply_markup=keyboards.admin_menu)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_company_selection: {e}")
        await callback.message.answer(constants.ERROR_MESSAGE)


class DeleteUserStates(StatesGroup):
    id = State()


@router.message(F.text == "❌ Remove user")
async def delete_user(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        users = await user_service.get_all()
        buttons = []
        for user in users:
            buttons.append([KeyboardButton(text=str(user.full_name))])

        buttons.append([KeyboardButton(text="⬅️ Cancel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        await state.set_state(DeleteUserStates.id)
        await message.answer("Select user: ", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in delete_user: {e}")
        await message.answer(constants.ERROR_MESSAGE)


@router.message(DeleteUserStates.id)
async def delete_user_by_id(message: Message, state: FSMContext):
    try:
        user_name = message.text.strip()
        user = await user_service.get_by_full_name(user_name)
        if not user:
            await message.answer("Please use buttons!")
            return

        await user_service.delete_by_id(user.id)
        await state.clear()
        await message.answer("✅ User deleted successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error in delete_user_by_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)
