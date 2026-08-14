from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import ContextTypes
from html import escape

from utils.targeting import resolve_target
from handlers.immunity_storage import is_immune


async def ban_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message
    chat = update.effective_chat

    # проверка админа
    admins = await context.bot.get_chat_administrators(
        chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    try:
        await message.delete()
    except:
        pass

    # определяем цель: ответом, по @username или по ID
    target_id, display_name, args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await chat.send_message(error)
        return

    # нельзя банить админов
    if target_id in admin_ids:
        await chat.send_message(
            "❌ Нельзя заблокировать администратора"
        )
        return

    # иммунитет защищает от бана (но не от antispam/antirepeat)
    if is_immune(chat.id, target_id):
        await chat.send_message(
            f"У @{escape(display_name)} [{target_id}] есть иммунитет "
            "— забанить нельзя."
        )
        return

    reason = " ".join(args)

    if not reason:
        reason = "Причина не указана"

    username = escape(display_name)

    # бан
    await context.bot.ban_chat_member(
        chat_id=chat.id,
        user_id=target_id
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Разблокировать",
                    callback_data=f"unban_{target_id}"
                )
            ]
        ]
    )

    await chat.send_message(
        text=(
            f"@{username} [{target_id}] "
            "заблокирован(а).\n\n"
            f"<b>Причина:</b> {escape(reason)}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def unban_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message
    chat = update.effective_chat

    admins = await context.bot.get_chat_administrators(
        chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    try:
        await message.delete()
    except:
        pass

    target_id, display_name, _args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await chat.send_message(error)
        return

    try:
        await context.bot.unban_chat_member(
            chat_id=chat.id,
            user_id=target_id
        )
    except Exception as e:
        print(f"UNBAN ERROR: {target_id} | {repr(e)}")

        await chat.send_message(
            "⚠️ Не удалось разблокировать пользователя"
        )
        return

    await chat.send_message(
        text=f"✅ {escape(display_name)} [{target_id}] разблокирован(а)."
    )


async def unban_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    # Проверяем права
    admins = await context.bot.get_chat_administrators(
        update.effective_chat.id
    )

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    # Остальной код снятия бана
    data = query.data

    user_id = int(
        data.replace("unban_", "")
    )

    await context.bot.unban_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id
    )

    await query.message.delete()
