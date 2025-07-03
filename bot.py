import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, ContextTypes, filters
)
from db import (
    init_db, get_booked_slots, add_booking,
    get_future_bookings, delete_booking, get_all_bookings
)
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "7825171005:AAFjH26MWNVuTOCDBGN0RZ4neA3ecg90MX8"  # ✅ Replace with your token
ADMIN_PASSWORD = "nikita123"            # ✅ Replace with your password
HOURS = list(range(12, 22))

# Conversation states
SELECT_DATE, SELECT_TIME, CONFIRM_CANCEL, ADMIN_AUTH, SELECT_PANEL_DATE, FORCE_CANCEL = range(6)

# In-memory admin session store
admin_sessions = set()

# --- Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 Welcome to the .clime training room Booking Bot!\n"
        "Use /book to reserve a time up to 7 days ahead.\n"
        "Use /cancel to cancel a future booking (1+ days ahead).\n"
    )

# --- Booking flow ---

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    keyboard = [
        [InlineKeyboardButton(date, callback_data=f"date_{date}")]
        for date in dates
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📅 Select a date to book:", reply_markup=reply_markup)
    return SELECT_DATE

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_date = query.data.split("_")[1]
    context.user_data['selected_date'] = selected_date

    booked = get_booked_slots(selected_date)
    free_hours = [h for h in HOURS if h not in booked]

    if not free_hours:
        await query.edit_message_text(f"❌ All slots booked for {selected_date}.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f"{h}:00", callback_data=f"time_{h}")]
        for h in free_hours
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🕒 Select an available time for {selected_date}:", reply_markup=reply_markup)
    return SELECT_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_hour = int(query.data.split("_")[1])
    date_str = context.user_data['selected_date']
    username = query.from_user.first_name or "Telegram User"

    success = add_booking(username, date_str, selected_hour)

    if success:
        await query.edit_message_text(f"✅ Booking confirmed for {date_str} at {selected_hour}:00.")
    else:
        await query.edit_message_text("❌ Sorry, that slot was just taken. Try /book again.")
    return ConversationHandler.END

# --- Cancel flow ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.first_name or "Telegram User"
    bookings = get_future_bookings(username)

    if not bookings:
        await update.message.reply_text(
            "❌ You have no bookings that can be cancelled.\n"
            "Bookings can only be cancelled 1+ days in advance."
        )
        return ConversationHandler.END

    keyboard = []
    for booking in bookings:
        booking_id, date, hour = booking
        label = f"{date} at {hour}:00"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cancel_{booking_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a booking to cancel:", reply_markup=reply_markup)
    return CONFIRM_CANCEL

async def confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.split("_")[1])
    delete_booking(booking_id)
    await query.edit_message_text("✅ Your booking has been cancelled.")
    return ConversationHandler.END

# --- Admin auth & panel ---

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Enter admin password:", reply_markup=ReplyKeyboardRemove())
    return ADMIN_AUTH

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ADMIN_PASSWORD:
        admin_sessions.add(update.effective_user.id)
        await update.message.reply_text(
            "✅ Admin login successful!\nUse /panel to view bookings.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        await update.message.reply_text("⛔ You are not authorized. Use /admin to login.")
        return ConversationHandler.END

    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    keyboard = [
        [InlineKeyboardButton(date, callback_data=f"panel_date_{date}")]
        for date in dates
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📅 Select a date to view bookings:", reply_markup=reply_markup)
    return SELECT_PANEL_DATE

async def show_panel_for_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    date_str = query.data.split("_")[2]

    bookings = get_all_bookings(date_str)

    if not bookings:
        await query.edit_message_text(f"No bookings found for {date_str}.")
        return ConversationHandler.END

    msg = f"📅 Bookings for {date_str}:\n"
    keyboard = []

    for booking in bookings:
        booking_id, username, hour = booking
        msg += f" - {hour}:00 → {username}\n"
        keyboard.append([InlineKeyboardButton(f"{hour}:00 {username}", callback_data=f"force_{booking_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg + "\nClick to force-cancel any:", reply_markup=reply_markup)
    return FORCE_CANCEL

async def force_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.split("_")[1])
    delete_booking(booking_id)
    await query.edit_message_text("✅ Booking has been force-cancelled by admin.")
    return ConversationHandler.END

# --- Main ---

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))

    book_handler = ConversationHandler(
        entry_points=[CommandHandler("book", book)],
        states={
            SELECT_DATE: [CallbackQueryHandler(select_date, pattern=r'^date_')],
            SELECT_TIME: [CallbackQueryHandler(select_time, pattern=r'^time_')],
        },
        fallbacks=[]
    )

    cancel_handler = ConversationHandler(
        entry_points=[CommandHandler("cancel", cancel)],
        states={CONFIRM_CANCEL: [CallbackQueryHandler(confirm_cancel, pattern=r'^cancel_\d+$')]},
        fallbacks=[]
    )

    admin_auth_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin)],
        states={ADMIN_AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)]},
        fallbacks=[]
    )

    panel_handler = ConversationHandler(
        entry_points=[CommandHandler("panel", panel)],
        states={
            SELECT_PANEL_DATE: [CallbackQueryHandler(show_panel_for_date, pattern=r'^panel_date_')],
            FORCE_CANCEL: [CallbackQueryHandler(force_cancel, pattern=r'^force_\d+$')],
        },
        fallbacks=[]
    )

    # Register once!
    app.add_handler(book_handler)
    app.add_handler(cancel_handler)
    app.add_handler(admin_auth_handler)
    app.add_handler(panel_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
