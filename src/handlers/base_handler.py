from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import *
from logger import logger

from src import keyboards
from src.functions import *
from src.services import user_service

router = Router()


@router.message(F.text == "⬅️ Cancel")
async def cancel(message: Message, state: FSMContext):
    try:
        if state:
            await state.clear()

        user_id = message.from_user.id

        if await is_admin(user_id):
            await message.answer("✅ Cancelled...", reply_markup=keyboards.admin_menu)
            return

        user = await user_service.get_by_id(user_id, constants.TELEGRAM_ID)
        if user:
            await message.answer("✅ Cancelled", reply_markup=keyboards.user_menu)
            return

    except:
        logger.error("Error in base handler, cancel")
        await message.answer(constants.ERROR_MESSAGE)
