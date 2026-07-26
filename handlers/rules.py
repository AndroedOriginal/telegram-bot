from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


RULES_LINK = "https://telegra.ph/Pravila-Nyuberg-CHata-12-03-2"


async def rules_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    try:
        await message.delete()
    except:
        pass


    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "тык",
                    url=RULES_LINK
                )
            ]
        ]
    )


    await update.effective_chat.send_message(
        text="<b>Правила группы:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
