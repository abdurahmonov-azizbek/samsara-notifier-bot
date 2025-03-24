from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import *
from src.logger import logger
from src.base import bot
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

@router.callback_query(lambda callback: callback.data == "cancel")
async def cancel_inline(callback: CallbackQuery, state: FSMContext):
    try:
        if state:
            await state.clear()

        user_id = callback.from_user.id

        if await is_admin(user_id):
            await bot.send_message(user_id, "✅ Cancelled...", reply_markup=keyboards.admin_menu)
            await callback.message.delete()
            return

        user = await user_service.get_by_id(user_id, constants.TELEGRAM_ID)
        if user:
            await bot.send_message(user_id, "✅ Cancelled", reply_markup=keyboards.user_menu)
            await callback.message.delete()
            return
    except:
        logger.error("Error in base handler, inline_cancel")
        await callback.answer(constants.ERROR_MESSAGE)