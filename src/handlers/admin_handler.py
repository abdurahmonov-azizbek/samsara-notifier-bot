from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F, Router
from functions import *
from aiogram.types import *
from logger import logger
import keyboards
import constants
from models import Company, User
from services import company_service, user_service

router =  Router()

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
        await message.answer(f"Enter api-key from samsara for <b>{company_name}</b>", reply_markup=keyboards.cancel_button, parse_mode="html")
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
    id = State()
    name = State()
    api_key = State()

@router.message(F.text == "✏️ Edit company")
async def edit_company(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return
        
        await state.set_state(EditCompanyStates.id)
        await message.answer("Enter id of the company: ", reply_markup=keyboards.cancel_button)

    except Exception as e:
        logger.error(f"Error while editing company: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditCompanyStates.id)
async def ask_new_name(message: Message, state: FSMContext):
    try:
        await state.update_data(id=int(message.text.strip()))
        await state.set_state(EditCompanyStates.name)
        await message.answer("Enter company's (new) name: ", reply_markup=keyboards.cancel_button)

    except Exception as e:
        logger.error(f"Error in ask_new_name: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditCompanyStates.name)
async def ask_new_api_key(message: Message, state: FSMContext):
    try:
        await state.update_data(name=message.text.strip())
        await state.set_state(EditCompanyStates.api_key)
        await message.answer("Enter (new) api-key: ", reply_markup=keyboards.cancel_button)

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
        
        await state.set_state(DeleteCompanyStates.id)
        await message.answer("Enter the company's id: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in delete_company: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(DeleteCompanyStates.id)
async def delete_company_by_id(message: Message, state: FSMContext):
    try:
        company_id = int(message.text.strip())
        await company_service.delete_by_id(company_id)
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

@router.message(AddUserStates.full_name)
async def ask_company_id(message: Message, state: FSMContext):
    try:
        full_name = message.text.strip()
        await state.update_data(full_name=full_name)
        await state.set_state(AddUserStates.company_id)
        await message.answer("Enter user's company ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in ask_company_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(AddUserStates.company_id)
async def save_user(message: Message, state: FSMContext):
    try:
        company_id = int(message.text.strip())
        data = await state.get_data()
        await state.clear()

        user = User(
            id=None,
            telegram_id=data['telegram_id'],
            full_name=data['full_name'],
            company_id=company_id,
            balance=0
        )
        await user_service.create(user)
        await message.answer("✅ User added successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error while saving user: {e}")
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
            text += f"<b>🆔 {user.id}</b>\n"
            text += f"<b>👤 {user.full_name}</b>\n"
            text += f"<b>📱 Telegram ID: {user.telegram_id}</b>\n"
            text += f"<b>🏢 Company ID: {user.company_id}</b>\n\n"

        await message.answer(text, parse_mode="html")
    except Exception as e:
        logger.error(f"Error while showing all users: {e}")
        await message.answer(constants.ERROR_MESSAGE)

class EditUserStates(StatesGroup):
    id = State()
    telegram_id = State()
    full_name = State()
    company_id = State()

@router.message(F.text == "✏️ Edit user")
async def edit_user(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        await state.set_state(EditUserStates.id)
        await message.answer("Enter the user's ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error while editing user: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditUserStates.id)
async def ask_new_telegram_id(message: Message, state: FSMContext):
    try:
        await state.update_data(id=int(message.text.strip()))
        await state.set_state(EditUserStates.telegram_id)
        await message.answer("Enter user's (new) Telegram ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in ask_new_telegram_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditUserStates.telegram_id)
async def ask_new_full_name(message: Message, state: FSMContext):
    try:
        await state.update_data(telegram_id=int(message.text.strip()))
        await state.set_state(EditUserStates.full_name)
        await message.answer("Enter user's (new) full name: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in ask_new_full_name: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditUserStates.full_name)
async def ask_new_company_id(message: Message, state: FSMContext):
    try:
        await state.update_data(full_name=message.text.strip())
        await state.set_state(EditUserStates.company_id)
        await message.answer("Enter user's (new) company ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in ask_new_company_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(EditUserStates.company_id)
async def save_updated_user(message: Message, state: FSMContext):
    try:
        company_id = int(message.text.strip())
        data = await state.get_data()
        await state.clear()

        user = User(
            id=data['id'],
            telegram_id=data['telegram_id'],
            full_name=data['full_name'],
            company_id=company_id,
            balance=0
        )
        await user_service.update(user)
        await message.answer("✅ User successfully updated", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error while updating user: {e}")
        await message.answer(constants.ERROR_MESSAGE)

class DeleteUserStates(StatesGroup):
    id = State()

@router.message(F.text == "❌ Remove user")
async def delete_user(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not await is_admin(user_id):
            return

        await state.set_state(DeleteUserStates.id)
        await message.answer("Enter the user's ID: ", reply_markup=keyboards.cancel_button)
    except Exception as e:
        logger.error(f"Error in delete_user: {e}")
        await message.answer(constants.ERROR_MESSAGE)

@router.message(DeleteUserStates.id)
async def delete_user_by_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await user_service.delete_by_id(user_id)
        await state.clear()
        await message.answer("✅ User deleted successfully", reply_markup=keyboards.admin_menu)
    except Exception as e:
        logger.error(f"Error in delete_user_by_id: {e}")
        await message.answer(constants.ERROR_MESSAGE)