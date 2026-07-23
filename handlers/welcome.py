from telegram import Update
from telegram.ext import ContextTypes


WELCOME_TEXT = """
Добро пожаловать в Нюберг чат!

Место, где ты можешь пообщаться с людьми на любые темы, поделиться хорошей музыкой и посоревноваться с другими участниками в играх.

Не забудь прочитать <a href="https://telegra.ph/Pravila-Nyuberg-CHata-12-03-2">правила</a> чата, перед началом общения, говорят, тут строгая модерация 👀
"""

async def welcome_new_member(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    for member in update.message.new_chat_members:

        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
