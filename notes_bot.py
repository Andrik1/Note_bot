#!/usr/bin/env python3
"""
Telegram Бот Нотатки & Список покупок (Українська версія)
===========================================================
Встановлення:
    pip install python-telegram-bot

Запуск:
    python notes_bot.py
"""

import os
import logging
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─── НАЛАШТУВАННЯ ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("8762144121:AAGOTcLHC4Xa5nRjHBCO9Uu9qzPVEhaKuCo")

# ─── СТАНИ ────────────────────────────────────────────────────────────────────
(
    STATE_MAIN,
    STATE_ADD_NOTE,
    STATE_ADD_SHOP_ITEM,
    STATE_NOTE_TITLE,
    STATE_NOTE_TEXT,
) = range(5)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── КАТЕГОРІЇ ────────────────────────────────────────────────────────────────
NOTE_CATEGORIES = {
    "📝": "Нотатки",
    "🛒": "Покупки",
    "💼": "Робота",
    "🏠": "Дім",
    "💡": "Ідеї",
    "❤️": "Особисте",
}

# ─── ПОМІЧНИКИ ────────────────────────────────────────────────────────────────
def get_notes(ctx) -> dict:
    return ctx.user_data.setdefault("notes", {})

def get_shop_list(ctx) -> list:
    return ctx.user_data.setdefault("shop_list", [])

def note_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")

def fmt_date(dt_str: str) -> str:
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return dt_str

def esc(s: str) -> str:
    for c in r"_.!*[]()~`>#+-=|{}":
        s = s.replace(c, f"\\{c}")
    return s

# ─── КЛАВІАТУРИ ───────────────────────────────────────────────────────────────
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📝 Нотатки"),  KeyboardButton("🛒 Список покупок")],
            [KeyboardButton("🔍 Пошук"),    KeyboardButton("📊 Статистика")],
            [KeyboardButton("❓ Допомога")],
        ],
        resize_keyboard=True,
    )

def notes_keyboard(notes: dict):
    buttons = []
    for nid, note in list(notes.items())[-10:]:
        emoji = note.get("category", "📝")
        title = note.get("title", "Без назви")[:25]
        buttons.append([InlineKeyboardButton(
            f"{emoji} {title}", callback_data=f"view_note:{nid}"
        )])
    buttons.append([
        InlineKeyboardButton("➕ Додати", callback_data="add_note"),
        InlineKeyboardButton("🗑 Видалити всі", callback_data="clear_notes"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

def note_view_keyboard(nid: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Видалити", callback_data=f"del_note:{nid}")],
        [InlineKeyboardButton("🔙 До нотаток", callback_data="show_notes")],
    ])

def category_keyboard():
    buttons = []
    row = []
    for emoji, name in NOTE_CATEGORIES.items():
        row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"cat:{emoji}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Скасувати", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

def shop_keyboard(shop_list: list):
    buttons = []
    for i, item in enumerate(shop_list):
        checked = item.get("checked", False)
        icon    = "✅" if checked else "⬜"
        name    = item.get("name", "")[:30]
        qty     = item.get("qty", "")
        label   = f"{icon} {name}" + (f" ({qty})" if qty else "")
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"toggle:{i}"),
            InlineKeyboardButton("🗑",  callback_data=f"del_item:{i}"),
        ])
    bottom = [InlineKeyboardButton("➕ Додати товар", callback_data="add_item")]
    if any(item.get("checked") for item in shop_list):
        bottom.append(InlineKeyboardButton("🧹 Прибрати куплене", callback_data="clear_checked"))
    if shop_list:
        bottom.append(InlineKeyboardButton("🗑 Очистити все", callback_data="clear_shop"))
    buttons.append(bottom)
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# ─── СТАРТ ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user        = update.effective_user
    notes_count = len(get_notes(ctx))
    shop_count  = len(get_shop_list(ctx))
    text = (
        f"👋 Привіт, *{esc(user.first_name)}*\\!\n\n"
        f"Я твій особистий блокнот у Telegram\\.\n\n"
        f"📝 Нотаток: *{notes_count}*\n"
        f"🛒 Товарів у списку: *{shop_count}*\n\n"
        f"Обери розділ 👇"
    )
    await update.message.reply_text(
        text, parse_mode="MarkdownV2", reply_markup=main_keyboard()
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Як користуватися:*\n\n"
        "📝 *Нотатки* — створюй, переглядай та видаляй нотатки за категоріями\n\n"
        "🛒 *Список покупок* — додавай товари, відмічай куплені галочкою\n\n"
        "🔍 *Пошук* — шукай по тексту нотаток\n\n"
        "📊 *Статистика* — скільки нотаток і покупок\n\n"
        "*Категорії нотаток:*\n"
        "📝 Нотатки · 🛒 Покупки · 💼 Робота\n"
        "🏠 Дім · 💡 Ідеї · ❤️ Особисте"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── НОТАТКИ ──────────────────────────────────────────────────────────────────
async def show_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    notes = get_notes(ctx)
    text  = f"📝 *Твої нотатки* \\({len(notes)} шт\\.\\):\n\n"

    if not notes:
        text += "_Нотаток поки немає\\. Натисни ➕ щоб додати\\._"
    else:
        by_cat = {}
        for nid, note in notes.items():
            cat = note.get("category", "📝")
            by_cat.setdefault(cat, []).append((nid, note))

        for cat_emoji, items in by_cat.items():
            cat_name = NOTE_CATEGORIES.get(cat_emoji, "Інше")
            text += f"\n*{cat_emoji} {esc(cat_name)}* \\({len(items)}\\):\n"
            for nid, note in items[-5:]:
                title = esc(note.get("title", "Без назви")[:30])
                date  = esc(fmt_date(note.get("date", "")))
                text += f"  • {title} _\\({date}\\)_\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=notes_keyboard(notes)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=notes_keyboard(notes)
        )


async def add_note_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 *Нова нотатка*\n\nОберіть категорію:",
        parse_mode="Markdown",
        reply_markup=category_keyboard(),
    )
    return STATE_NOTE_TITLE


async def select_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    cat      = query.data.split(":")[1]
    ctx.user_data["new_note_cat"] = cat
    cat_name = NOTE_CATEGORIES.get(cat, "Нотатка")
    await query.edit_message_text(
        f"*{cat} {cat_name}*\n\nВведіть *заголовок* нотатки:",
        parse_mode="Markdown",
    )
    return STATE_NOTE_TITLE


async def note_title_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if len(title) > 100:
        await update.message.reply_text(
            "❌ Заголовок занадто довгий \\(макс\\. 100 символів\\)\\.",
            parse_mode="MarkdownV2"
        )
        return STATE_NOTE_TITLE
    ctx.user_data["new_note_title"] = title
    await update.message.reply_text(
        f"✅ Заголовок: *{esc(title)}*\n\nТепер введіть *текст* нотатки:",
        parse_mode="MarkdownV2",
    )
    return STATE_NOTE_TEXT


async def note_text_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text.strip()
    nid   = note_id()
    notes = get_notes(ctx)
    notes[nid] = {
        "title":    ctx.user_data.get("new_note_title", "Без назви"),
        "text":     text,
        "category": ctx.user_data.get("new_note_cat", "📝"),
        "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    cat     = ctx.user_data.get("new_note_cat", "📝")
    title   = ctx.user_data.get("new_note_title", "")
    snippet = text[:100] + ("..." if len(text) > 100 else "")
    await update.message.reply_text(
        f"✅ *Нотатку збережено\\!*\n\n"
        f"{cat} *{esc(title)}*\n\n_{esc(snippet)}_",
        parse_mode="MarkdownV2",
        reply_markup=main_keyboard(),
    )
    return ConversationHandler.END


async def view_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nid   = query.data.split(":")[1]
    notes = get_notes(ctx)
    note  = notes.get(nid)
    if not note:
        await query.edit_message_text("❌ Нотатку не знайдено.")
        return
    cat   = note.get("category", "📝")
    title = note.get("title", "Без назви")
    text  = note.get("text", "")
    date  = fmt_date(note.get("date", ""))
    msg   = f"{cat} *{esc(title)}*\n_📅 {esc(date)}_\n\n{esc(text)}"
    await query.edit_message_text(
        msg, parse_mode="MarkdownV2", reply_markup=note_view_keyboard(nid)
    )


async def delete_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    nid   = query.data.split(":")[1]
    notes = get_notes(ctx)
    title = notes.pop(nid, {}).get("title", "нотатка")
    await query.answer(f"🗑 «{title}» видалено")
    await show_notes(update, ctx)


async def clear_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["notes"] = {}
    await query.edit_message_text(
        "🗑 Всі нотатки видалено\\.", parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Додати нотатку", callback_data="add_note")
        ]])
    )


# ─── СПИСОК ПОКУПОК ───────────────────────────────────────────────────────────
async def show_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop    = get_shop_list(ctx)
    total   = len(shop)
    checked = sum(1 for i in shop if i.get("checked"))
    text    = f"🛒 *Список покупок* \\({checked}/{total}\\)\n\n"

    if not shop:
        text += "_Список порожній\\. Натисни ➕ щоб додати товар\\._"
    else:
        for item in shop:
            icon = "✅" if item.get("checked") else "⬜"
            name = esc(item.get("name", ""))
            qty  = item.get("qty", "")
            line = f"{icon} {name}"
            if qty:
                line += f" — _{esc(qty)}_"
            text += line + "\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=shop_keyboard(shop)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=shop_keyboard(shop)
        )


async def add_item_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛒 *Додати товар*\n\n"
        "Введіть назву товару\\:\n"
        "_\\(або назву і кількість через кому: Молоко, 2л\\)_\n\n"
        "_Можна додати кілька товарів — кожен з нового рядка_",
        parse_mode="MarkdownV2",
    )
    return STATE_ADD_SHOP_ITEM


async def item_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text.strip()
    shop  = get_shop_list(ctx)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    added = []
    for line in lines:
        parts = [p.strip() for p in line.split(",", 1)]
        name  = parts[0]
        qty   = parts[1] if len(parts) > 1 else ""
        shop.append({"name": name, "qty": qty, "checked": False})
        added.append(name)
    names = ", ".join(added)
    await update.message.reply_text(
        f"✅ Додано: *{esc(names)}*",
        parse_mode="MarkdownV2",
        reply_markup=main_keyboard(),
    )
    await update.message.reply_text(
        "🛒 Список оновлено\\!",
        parse_mode="MarkdownV2",
        reply_markup=shop_keyboard(shop),
    )
    return ConversationHandler.END


async def toggle_item(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx  = int(query.data.split(":")[1])
    shop = get_shop_list(ctx)
    if 0 <= idx < len(shop):
        shop[idx]["checked"] = not shop[idx].get("checked", False)
    await show_shop(update, ctx)


async def delete_item(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    idx   = int(query.data.split(":")[1])
    shop  = get_shop_list(ctx)
    if 0 <= idx < len(shop):
        name = shop.pop(idx).get("name", "товар")
        await query.answer(f"🗑 «{name}» видалено")
    else:
        await query.answer()
    await show_shop(update, ctx)


async def clear_checked(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["shop_list"] = [i for i in get_shop_list(ctx) if not i.get("checked")]
    await show_shop(update, ctx)


async def clear_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["shop_list"] = []
    await show_shop(update, ctx)


# ─── ПОШУК ────────────────────────────────────────────────────────────────────
async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["searching"] = True
    await update.message.reply_text(
        "🔍 *Пошук по нотатках*\n\nВведіть текст для пошуку:",
        parse_mode="Markdown",
    )


async def do_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("searching"):
        return await text_router(update, ctx)
    ctx.user_data["searching"] = False
    q      = update.message.text.strip().lower()
    notes  = get_notes(ctx)
    results = [
        (nid, note) for nid, note in notes.items()
        if q in note.get("title", "").lower() or q in note.get("text", "").lower()
    ]
    if not results:
        await update.message.reply_text(
            f"🔍 За запитом *«{esc(q)}»* нічого не знайдено\\.",
            parse_mode="MarkdownV2", reply_markup=main_keyboard(),
        )
        return
    text_out = f"🔍 Знайдено *{len(results)}* нотаток:\n\n"
    for nid, note in results:
        cat     = note.get("category", "📝")
        title   = esc(note.get("title", ""))
        snippet = esc(note.get("text", "")[:60])
        text_out += f"{cat} *{title}*\n_{snippet}\\.\\.\\._\n\n"
    await update.message.reply_text(
        text_out, parse_mode="MarkdownV2", reply_markup=main_keyboard()
    )


# ─── СТАТИСТИКА ───────────────────────────────────────────────────────────────
async def show_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    notes   = get_notes(ctx)
    shop    = get_shop_list(ctx)
    by_cat  = {}
    for note in notes.values():
        cat = note.get("category", "📝")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    checked = sum(1 for i in shop if i.get("checked"))
    text = "📊 *Статистика*\n\n"
    text += f"📝 Всього нотаток: *{len(notes)}*\n"
    if by_cat:
        text += "\n*За категоріями:*\n"
        for cat, count in by_cat.items():
            name = NOTE_CATEGORIES.get(cat, "Інше")
            text += f"  {cat} {name}: *{count}*\n"
    text += f"\n🛒 Товарів у списку: *{len(shop)}*\n"
    text += f"  ✅ Куплено: *{checked}*\n"
    text += f"  ⬜ Залишилось: *{len(shop) - checked}*\n"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


# ─── РОУТЕР ───────────────────────────────────────────────────────────────────
async def text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📝 Нотатки":
        await show_notes(update, ctx)
    elif text == "🛒 Список покупок":
        await show_shop(update, ctx)
    elif text == "🔍 Пошук":
        await search_start(update, ctx)
    elif text == "📊 Статистика":
        await show_stats(update, ctx)
    elif text == "❓ Допомога":
        await cmd_help(update, ctx)
    else:
        await do_search(update, ctx)


async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "back":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Оберіть розділ 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Нотатки",        callback_data="show_notes")],
                [InlineKeyboardButton("🛒 Список покупок", callback_data="show_shop")],
            ])
        )
    elif data == "show_notes":   await show_notes(update, ctx)
    elif data == "show_shop":    await show_shop(update, ctx)
    elif data.startswith("view_note:"): await view_note(update, ctx)
    elif data.startswith("del_note:"):  await delete_note(update, ctx)
    elif data == "clear_notes":  await clear_notes(update, ctx)
    elif data.startswith("toggle:"):    await toggle_item(update, ctx)
    elif data.startswith("del_item:"):  await delete_item(update, ctx)
    elif data == "clear_checked": await clear_checked(update, ctx)
    elif data == "clear_shop":   await clear_shop(update, ctx)
    elif data == "cancel":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Скасовано.")


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    note_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_note_start, pattern="^add_note$")],
        states={
            STATE_NOTE_TITLE: [
                CallbackQueryHandler(select_category, pattern="^cat:"),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_title_received),
            ],
            STATE_NOTE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_text_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_item_start, pattern="^add_item$")],
        states={
            STATE_ADD_SHOP_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, item_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(note_conv)
    app.add_handler(shop_conv)
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("📝 Бот нотаток запущено! Натисніть Ctrl+C для зупинки.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
