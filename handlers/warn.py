import json
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


FILE = "data/warnings.json"


def load_warnings():
    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_warnings(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


async def warn_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Ответьте на сообщение пользователя, которого хотите предупредить."
        )
        return


    user = update.message.reply_to_message.from_user


    reason = " ".join(
        context.args
    )

    if not reason:
        reason = "Причина не указана"


    warnings = load_warnings()


    user_id = str(user.id)


    if user_id not in warnings:
        warnings[user_id] = 0


    warnings[user_id] += 1


    count = warnings[user_id]


    save_warnings(warnings)


    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отменить предупреждение",
                    callback_data=f"remove_warn_{user_id}"
                )
            ]
        ]
    )


    await update.message.reply_text(
        f"@{user.username} [{user.id}] предупреждён ({count}/3).\n\n"
        f"<b>Причина:</b> {reason}",
        parse_mode="HTML",
        reply_markup=keyboard
    )
