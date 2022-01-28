from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUPS = 5


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if chat.type == chat.PRIVATE:
        if args:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "Turned on reporting! You'll be notified whenever anyone reports something."
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Turned off reporting! You wont get any reports.")
        else:
            msg.reply_text(
                "Your current report preference is: `{}`".format(
                    sql.user_should_report(chat.id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

    elif args:
        if args[0] in ("yes", "on"):
            sql.set_chat_setting(chat.id, True)
            msg.reply_text(
                "Turned on reporting! Admins who have turned on reports will be notified when /report "
                "or @admin are called."
            )

        elif args[0] in ("no", "off"):
            sql.set_chat_setting(chat.id, False)
            msg.reply_text(
                "Turned off reporting! No admins will be notified on /report or @admin."
            )
    else:
        msg.reply_text(
            "This chat's current setting is: `{}`".format(
                sql.chat_should_report(chat.id)
            ),
            parse_mode=ParseMode.MARKDOWN,
        )


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        if reported_user.id == bot.id:
            message.reply_text("Haha nope, not gonna report myself.")
            return ""
        admin_list = chat.get_administrators()

        ping_list = "".join(
            f"​[​](tg://user?id={admin.user.id})"
            for admin in admin_list
            if not admin.user.is_bot
        )


        message.reply_text(
            f"Successfully reported [{reported_user.first_name}](tg://user?id={reported_user.id}) to admins! "
            + ping_list,
            parse_mode=ParseMode.MARKDOWN,
        )

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is setup to send user reports to admins, via /report and @admin: `{}`".format(
        sql.chat_should_report(chat_id)
    )


def __user_settings__(user_id):
    return "You receive reports from chats you're admin in: `{}`.\nToggle this with /reports in PM.".format(
        sql.user_should_report(user_id)
    )


__mod_name__ = "Reporting"

__help__ = """
 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.
NOTE: neither of these will get triggered if used by admins

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)

dispatcher.add_handler(REPORT_HANDLER, group=REPORT_GROUPS)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, group=REPORT_GROUPS)
dispatcher.add_handler(SETTING_HANDLER)
