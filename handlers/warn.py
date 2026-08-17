from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.ext import ContextTypes

from html import escape
from datetime import datetime, timedelta, timezone

from handlers.storage import (
    add_warn,
    remove_warn,
    reset_warn
)
from utils.targeting import resolve_target, EVERYONE, get_everyone_ids
from handlers.immunity_storage import is_immune


async def _bulk_warn(context, chat_id, admin_ids, args):
    reason = " ".join(args) or "Причина не указана"
    ids = await get_everyone_ids(context, chat_id, admin_ids)

    warned = 0
    muted_for_third = 0

    for uid in ids:
        count = add_warn(chat_id, uid)

        if count >= 3:
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=uid,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now(timezone.utc) + timedelta(minutes=10)
                )
            except Exception as e:
                print(f"WARN EVERYONE MUTE ERROR: {uid} | {repr(e)}")

            reset_warn(chat_id, uid)
            muted_for_third += 1
        else:
            warned += 1

    total = warned + muted_for_third

    print(
        f"WARN EVERYONE: {total} участников в чате {chat_id} | "
        f"замучено за 3/3: {muted_for_third} | причина: {reason}"
    )

    text = (
        f"Выдано предупреждений: {total}.\n\n"
        f"<b>Причина:</b> {escape(reason)}"
    )

    if muted_for_third:
        text += f"\n\nИз них замучено на 10 минут за 3/3: {muted_for_third}."

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML"
    )


async def warn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

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

    user_id, display_name, args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await update.effective_chat.send_message(error)
        return

    if user_id == EVERYONE:
        await _bulk_warn(context, chat_id, admin_ids, args)
        return

    # иммунитет защищает от варна (но не от antispam/antirepeat)
    if is_immune(chat_id, user_id):
        await update.effective_chat.send_message(
            f"У @{escape(display_name)} [{user_id}] есть иммунитет "
            "— выдать предупреждение нельзя."
        )
        return

    reason = " ".join(args)

    if not reason:
        reason = "Причина не указана"

    count = add_warn(chat_id, user_id)

    # ======= Третий варн =======

    if count >= 3:

        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            # ВАЖНО: Telegram нужен момент окончания, а не timedelta.
            until_date=datetime.now(timezone.utc) + timedelta(minutes=10)
        )

        reset_warn(chat_id, user_id)

        return

    # ======= Первый и второй =======

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"cancel_warn_{user_id}"
                )
            ]
        ]
    )

    username = escape(display_name)
    reason = escape(reason)

    await update.effective_chat.send_message(
        text=(
            f"@{username} [{user_id}] предупреждён ({count}/3).\n\n"
            f"<b>Причина:</b> {reason}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def unwarn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

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

    user_id, display_name, _args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await update.effective_chat.send_message(error)
        return

    if user_id == EVERYONE:
        # Иммунитет тут не помеха — он защищает от выдачи варна,
        # а не от его снятия.
        ids = await get_everyone_ids(
            context, chat_id, admin_ids, exclude_immune=False
        )

        for uid in ids:
            remove_warn(chat_id, uid)

        await update.effective_chat.send_message(
            f"✅ Предупреждения сняты со всех участников ({len(ids)})."
        )
        return

    count = remove_warn(chat_id, user_id)

    await update.effective_chat.send_message(
        text=(
            f"✅ Снято предупреждение с @{escape(display_name)} "
            f"[{user_id}] ({count}/3)."
        )
    )


async def cancel_warn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    chat_id = update.effective_chat.id

    # Проверяем, является ли нажавший администратором
    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    data = query.data

    user_id = int(
        data.replace("cancel_warn_", "")
    )

    remove_warn(chat_id, user_id)

    await query.message.delete()
