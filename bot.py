from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO

import database as db
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")

CURRENCIES = ["UAH", "USD", "EUR"]

BTN_ADD_EXPENSE = "➕ Додати витрату"
BTN_ADD_INCOME = "💰 Додати надходження"
BTN_DELETE_LAST = "🗑 Видалити останній запис"
BTN_STATS = "📊 Статистика"
BTN_SET_BUDGET = "💵 Встановити бюджет"
BTN_CHART = "📈 Графік витрат"
BTN_MANAGE_ENTRIES = "🗂 Мої записи"
CAT_FOOD = "🍔 Їжа"
CAT_TRANSPORT = "🚗 Транспорт"
CAT_HOME = "🏠 Житло"
CAT_FUN = "🎉 Розваги"
CAT_HEALTH = "💊 Здоров'я"
CAT_SHOPPING = "🛍 Покупки"
CAT_TECH = "💻 Техніка"
CAT_GIFTS = "🎁 Подарунки"
CAT_OTHER = "📦 Інше"

CATEGORIES_LIST = [
    CAT_FOOD, CAT_TRANSPORT, CAT_HOME, CAT_FUN,
    CAT_HEALTH, CAT_SHOPPING, CAT_TECH, CAT_GIFTS, CAT_OTHER
]

BTN_TODAY = "📅 Сьогодні"
BTN_WEEK = "🗓 Тиждень"
BTN_MONTH = "📆 Місяць"
BTN_ALL_TIME = "🗂 Весь час"
BTN_BACK = "⬅️ Назад"

CATEGORY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [CAT_FOOD, CAT_TRANSPORT],
        [CAT_HOME, CAT_FUN],
        [CAT_HEALTH, CAT_SHOPPING],
        [CAT_TECH, CAT_GIFTS],
        [CAT_OTHER],
        [BTN_BACK],
    ],
    resize_keyboard=True
)

STATS_MENU = ReplyKeyboardMarkup(
    [[BTN_TODAY, BTN_WEEK], [BTN_MONTH, BTN_ALL_TIME], [BTN_BACK]],
    resize_keyboard=True
)

CATEGORY_EMOJIS = {
    "їж": "🍔",
    "кав": "☕",
    "транспорт": "🚗",
    "таксі": "🚕",
    "житл": "🏠",
    "оренд": "🏠",
    "комунал": "🏠",
    "здоров": "💊",
    "лік": "💊",
    "розваг": "🎉",
    "кіно": "🎬",
    "покуп": "🛍",
    "одяг": "👕",
    "подар": "🎁",
    "др": "🎂",
    "день народ": "🎂",
    "техн": "💻",
    "пк": "💻",
    "телефон": "📱",
    "спорт": "🏋️",
    "подорож": "✈️",
    "тварин": "🐾",
    "освіт": "📚",
    "книг": "📚",
}


def get_category_emoji(category):
    category_lower = category.lower()
    for keyword, emoji in CATEGORY_EMOJIS.items():
        if keyword in category_lower:
            return emoji
    return "📦"


# Меню, яке буде висіти внизу екрана після вибору валюти
MAIN_MENU = ReplyKeyboardMarkup(
    [[BTN_ADD_EXPENSE, BTN_ADD_INCOME], [BTN_DELETE_LAST, BTN_STATS],
     [BTN_SET_BUDGET, BTN_CHART], [BTN_MANAGE_ENTRIES]],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    currency = db.get_user_currency(user_id)

    if currency:
        await update.message.reply_text(
            f"З поверненням! Твоя валюта: {currency}",
            reply_markup=MAIN_MENU
        )
    else:
        keyboard = ReplyKeyboardMarkup([CURRENCIES], resize_keyboard=True)
        await update.message.reply_text(
            "Привіт! Я FinHelper 💰\n\nОбери валюту, в якій рахуватимемо витрати:",
            reply_markup=keyboard
        )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, since_date, label):
    user_id = update.effective_user.id
    currency = db.get_user_currency(user_id)

    expenses = db.get_expenses_since(user_id, since_date)
    income = db.get_income_since(user_id, since_date)

    total_expenses = sum(row[0] for row in expenses)
    total_income = sum(row[0] for row in income)
    balance = total_income - total_expenses

    lines = [f"📊 СТАТИСТИКА: {label}", "➖➖➖➖➖➖➖➖➖➖"]

    if expenses:
        lines.append("\n💸 Витрати:")
        for amount, category, created_at in expenses:
            date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            date_text = date_obj.strftime("%d.%m.%Y")
            emoji = get_category_emoji(category)
            lines.append(f"{emoji} {date_text} — {amount:.2f} {currency} — {category}")
    else:
        lines.append("\nВитрат за цей період немає.")

    if income:
        lines.append("\n💰 Надходження:")
        for amount, created_at in income:
            date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            date_text = date_obj.strftime("%d.%m.%Y")
            lines.append(f"💵 {date_text} — {amount:.2f} {currency}")

    lines.append("\n➖➖➖➖➖➖➖➖➖➖")
    lines.append(f"🔻 Всього витрачено: {total_expenses:.2f} {currency}")
    lines.append(f"🔺 Всього надійшло: {total_income:.2f} {currency}")
    lines.append(f"📈 Баланс: {balance:.2f} {currency}")

    await update.message.reply_text("\n".join(lines))

async def show_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    currency = db.get_user_currency(user_id)
    expenses = db.get_all_expenses(user_id)

    if not expenses:
        await update.message.reply_text("Поки що витрат немає — нема що показувати на графіку.")
        return

    totals = {}
    for amount, category, created_at in expenses:
        if category in CATEGORIES_LIST:
            totals[category] = totals.get(category, 0) + amount

    if not totals:
        await update.message.reply_text(
            "Немає витрат з офіційних категорій для побудови графіка."
        )
        return

    # Сортуємо категорії від найбільшої суми до найменшої
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, values, color="#4C9AFF")

    # Підписуємо суму над кожним стовпчиком
    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.0f}",
            ha="center", va="bottom", fontsize=9
        )

    plt.title(f"Витрати за категоріями ({currency})")
    plt.ylabel(f"Сума ({currency})")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    plt.close()

    await update.message.reply_photo(photo=buffer)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Як користуватись FinHelper:\n\n"
        "➕ Додати витрату — записати, скільки і на що витратив\n"
        "💰 Додати надходження — записати дохід (зарплата, подарунок тощо)\n"
        "🗑 Видалити останній запис — прибрати останній запис, якщо помилився\n"
        "📊 Статистика — переглянути витрати/надходження за період\n"
        "💵 Встановити бюджет — задати місячний ліміт витрат\n"
        "📈 Графік витрат — кругова діаграма витрат по категоріях\n\n"
        "Якщо бот не розуміє повідомлення — просто натисни на потрібну кнопку внизу екрана 👇"
    )

async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я поки що розумію лише текстові повідомлення 🙂\nОбери дію кнопками внизу 👇"
    )

async def error_handler(update, context):
    logger.error(f"Виникла помилка: {context.error}")       

async def show_recent_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    currency = db.get_user_currency(user_id)
    entries = db.get_recent_entries(user_id, limit=10)

    if not entries:
        await update.message.reply_text("Поки що немає жодного запису.")
        return

    lines = ["🗂 Твої останні записи:\n"]
    for entry_id, amount, category, entry_type, created_at in entries:
        date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        date_text = date_obj.strftime("%d.%m.%Y")
        if entry_type == "income":
            lines.append(f"#{entry_id} — 💰 {date_text} — надходження {amount:.2f} {currency}")
        else:
            emoji = get_category_emoji(category)
            lines.append(f"#{entry_id} — {emoji} {date_text} — {amount:.2f} {currency} — {category}")

    lines.append("\nЩоб видалити запис, просто напиши його номер, наприклад:\n5")

    context.user_data["waiting_for"] = "delete_number"
    back_keyboard = ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)
    await update.message.reply_text("\n".join(lines), reply_markup=back_keyboard)

    if not context.args:
        await update.message.reply_text("Напиши номер запису, наприклад:\n/delete 5")
        return

    try:
        entry_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер запису має бути числом, наприклад:\n/delete 5")
        return

    deleted = db.delete_entry_by_id(entry_id, user_id)
    if deleted:
        await update.message.reply_text(f"Запис #{entry_id} видалено ✅")
    else:
        await update.message.reply_text("Такого запису не знайдено (можливо, він вже видалений).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # Якщо користувач обирає валюту
    if text in CURRENCIES:
        db.save_user_currency(user_id, text)
        await update.message.reply_text(
            f"Готово! Валюта обліку: {text} ✅",
            reply_markup=MAIN_MENU
        )
        return

    # Якщо користувач ще не обрав валюту — нічого більше не робимо
    currency = db.get_user_currency(user_id)
    if not currency:
        await update.message.reply_text("Спочатку введи команду /start і обери валюту 🙂")
        return

    # Обробка натискань кнопок меню
    if text == BTN_ADD_EXPENSE:
        context.user_data["waiting_for"] = "category"
        await update.message.reply_text("Обери категорію витрати:", reply_markup=CATEGORY_KEYBOARD)
        return

    if text == BTN_ADD_INCOME:
        context.user_data["waiting_for"] = "income"
        await update.message.reply_text(
            "Введи суму надходження, наприклад:\n5000",
            reply_markup=ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)
        )
        return

    # Якщо бот зараз чекає номер запису для видалення
    # Якщо бот зараз чекає номер запису для видалення
    if context.user_data.get("waiting_for") == "delete_number":
        if text == BTN_BACK:
            context.user_data["waiting_for"] = None
            await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
            return

        try:
            entry_id = int(text)
        except ValueError:
            await update.message.reply_text("Напиши, будь ласка, номер запису (просто число), наприклад:\n5")
            return

        deleted = db.delete_entry_by_id(entry_id, user_id)
        context.user_data["waiting_for"] = None

        if deleted:
            await update.message.reply_text(f"Запис #{entry_id} видалено ✅", reply_markup=MAIN_MENU)
        else:
            await update.message.reply_text(
                "Такого запису не знайдено (можливо, він вже видалений).",
                reply_markup=MAIN_MENU
            )
        return

    if text == BTN_DELETE_LAST:
        deleted = db.delete_last_entry(user_id)
        if deleted:
            await update.message.reply_text("Останній запис видалено 🗑")
        else:
            await update.message.reply_text("Поки що немає записів для видалення.")
        return

    if text == BTN_SET_BUDGET:
        context.user_data["waiting_for"] = "budget"
        await update.message.reply_text(
            "Введи суму місячного бюджету, наприклад:\n10000",
            reply_markup=ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)
        )
        return

    if text == BTN_CHART:
        await show_chart(update, context)
        return
    
    if text == BTN_MANAGE_ENTRIES:
        await show_recent_entries(update, context)
        return

    if text == BTN_STATS:
        await update.message.reply_text("За який період показати статистику?", reply_markup=STATS_MENU)
        return

    if text == BTN_TODAY:
        now = datetime.now()
        since = now.strftime("%Y-%m-%d 00:00:00")
        label = f"Сьогодні ({now.strftime('%d.%m.%Y')})"
        await show_stats(update, context, since, label)
        return

    if text == BTN_WEEK:
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        since = week_ago.strftime("%Y-%m-%d %H:%M:%S")
        label = f"з {week_ago.strftime('%d.%m.%Y')} по {now.strftime('%d.%m.%Y')}"
        await show_stats(update, context, since, label)
        return

    if text == BTN_MONTH:
        now = datetime.now()
        month_ago = now - timedelta(days=30)
        since = month_ago.strftime("%Y-%m-%d %H:%M:%S")
        label = f"з {month_ago.strftime('%d.%m.%Y')} по {now.strftime('%d.%m.%Y')}"
        await show_stats(update, context, since, label)
        return

    if text == BTN_ALL_TIME:
        now = datetime.now()
        since = "2000-01-01 00:00:00"
        label = f"Весь час (по {now.strftime('%d.%m.%Y')})"
        await show_stats(update, context, since, label)
        return

    if text == BTN_BACK:
        await update.message.reply_text("Обери дію з меню нижче:", reply_markup=MAIN_MENU)
        return

    # Якщо бот зараз чекає вибір категорії
    if context.user_data.get("waiting_for") == "category":
        if text == BTN_BACK:
            await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
            return

        if text not in CATEGORIES_LIST:
            await update.message.reply_text("Обери категорію за допомогою кнопок нижче 👇")
            return

        context.user_data["category"] = text
        context.user_data["waiting_for"] = "expense_amount"
        await update.message.reply_text(
            f"Категорія: {text}\n\nТепер введи суму витрати, наприклад:\n150",
            reply_markup=ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)
        )
        return

    # Якщо бот зараз чекає суму витрати
    # Якщо бот зараз чекає суму витрати (категорію вже обрано)
    if context.user_data.get("waiting_for") == "expense_amount":
        if text == BTN_BACK:
            context.user_data["waiting_for"] = None
            await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
            return

        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Введи, будь ласка, число, наприклад:\n150")
            return

        category = context.user_data.get("category", CAT_OTHER)
        db.add_expense(user_id, amount, category)
        context.user_data["waiting_for"] = None

        message = f"Записано витрату: {amount:.2f} {currency} — {category} ✅"

        budget = db.get_budget(user_id)
        if budget > 0:
            since = datetime.now().strftime("%Y-%m-01 00:00:00")
            month_expenses = db.get_expenses_since(user_id, since)
            total_this_month = sum(row[0] for row in month_expenses)
            percent = (total_this_month / budget) * 100

            if total_this_month > budget:
                message += f"\n\n🔴 Увага! Ти перевищив місячний бюджет ({budget:.2f} {currency}). Витрачено вже {total_this_month:.2f} {currency}."
            elif percent >= 80:
                message += f"\n\n🟡 Увага! Ти витратив вже {percent:.0f}% місячного бюджету ({total_this_month:.2f} з {budget:.2f} {currency})."

        await update.message.reply_text(message, reply_markup=MAIN_MENU)
        return

    # Якщо бот зараз чекає суму бюджету
    if context.user_data.get("waiting_for") == "budget":
        if text == BTN_BACK:
            context.user_data["waiting_for"] = None
            await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
            return

        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Введи, будь ласка, число, наприклад:\n10000")
            return

        db.set_budget(user_id, amount)
        context.user_data["waiting_for"] = None
        await update.message.reply_text(
            f"Місячний бюджет встановлено: {amount:.2f} {currency} ✅",
            reply_markup=MAIN_MENU
        )
        return

    # Якщо бот зараз чекає суму надходження
    if context.user_data.get("waiting_for") == "income":
        if text == BTN_BACK:
            context.user_data["waiting_for"] = None
            await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
            return

        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Введи, будь ласка, число, наприклад:\n5000")
            return

        db.add_income(user_id, amount)
        context.user_data["waiting_for"] = None
        await update.message.reply_text(
            f"Записано надходження: {amount:.2f} {currency} ✅",
            reply_markup=MAIN_MENU
        )
        return

    # Якщо нічого з вищого не підійшло
    await update.message.reply_text("Обери дію за допомогою кнопок унизу 👇", reply_markup=MAIN_MENU)


def main():
    db.init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(~filters.TEXT, handle_non_text))
    application.add_error_handler(error_handler)

    print("Бот запущено...")
    application.run_polling()


if __name__ == "__main__":
    main()
