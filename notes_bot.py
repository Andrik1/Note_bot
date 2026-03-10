#!/usr/bin/env python3
"""
Telegram Notes & Shopping List Bot
====================================
Бот для заметок и списков покупок.

Установка:
    pip install python-telegram-bot

Запуск:
    python notes_bot.py
"""

import os
import json
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

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ─── СОСТОЯНИЯ ────────────────────────────────────────────────────────────────
(
    STATE_MAIN,
    STATE_ADD_NOTE,
    STATE_ADD_SHOP_ITEM,
    STATE_VIEW_NOTES,
    STATE_NOTE_TITLE,
    STATE_NOTE_TEXT,
    STATE_EDIT_NOTE,
    STATE_RENAME_CATEGORY,
) = range(8)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── КАТЕГОРИИ ЗАМЕТОК ────────────────────────────────────────────────────────
NOTE_CATEGORIES = {
    "📝": "Заметки",
    "🛒": "Покупки",
    "💼": "Работа",
    "🏠": "Дом",
    "💡": "Идеи",
    "❤️": "Личное",
}

# ─── ХЕЛПЕРЫ ──────────────────────────────────────────────────────────────────
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

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📝 Заметки"),   KeyboardButton("🛒 Список покупок")],
            [KeyboardButton("🔍 Поиск"),     KeyboardButton("📊 Статистика")],
            [KeyboardButton("❓ Помощь")],
        ],
        resize_keyboard=True,
    )

def notes_keyboard(notes: dict):
    buttons = []
    for nid, note in list(notes.items())[-10:]:  # последние 10
        emoji = note.get("category", "📝")
        title = note.get("title", "Без названия")[:25]
        buttons.append([InlineKeyboardButton(
            f"{emoji} {title}", callback_data=f"view_note:{nid}"
        )])
    buttons.append([
        InlineKeyboardButton("➕ Добавить", callback_data="add_note"),
        InlineKeyboardButton("🗑 Очистить все", callback_data="clear_notes"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

def note_view_keyboard(nid: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_note:{nid}"),
            InlineKeyboardButton("🗑 Удалить",        callback_data=f"del_note:{nid}"),
        ],
        [InlineKeyboardButton("🔙 К заметкам", callback_data="show_notes")],
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
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
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
            InlineKeyboardButton("🗑", callback_data=f"del_item:{i}"),
        ])
    bottom = [
        InlineKeyboardButton("➕ Добавить", callback_data="add_item"),
    ]
    if any(item.get("checked") for item in shop_list):
        bottom.append(InlineKeyboardButton("🧹 Убрать купленное", callback_data="clear_checked"))
    if shop_list:
        bottom.append(InlineKeyboardButton("🗑 Очистить всё", callback_data="clear_shop"))
    buttons.append(bottom)
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# ─── СТАРТ ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    notes_count = len(get_notes(ctx))
    shop_count  = len(get_shop_list(ctx))

    text = (
        f"👋 Привет, *{user.first_name}*\\!\n\n"
        f"Я твой личный блокнот в Telegram\\.\n\n"
        f"📝 Заметок: *{notes_count}*\n"
        f"🛒 Товаров в списке: *{shop_count}*\n\n"
        f"Выбери раздел 👇"
    )
    await update.message.reply_text(
        text, parse_mode="MarkdownV2", reply_markup=main_keyboard()
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Как пользоваться:*\n\n"
        "📝 *Заметки* — создавай, редактируй, удаляй заметки по категориям\n\n"
        "🛒 *Список покупок* — добавляй товары, отмечай купленные галочкой\n\n"
        "🔍 *Поиск* — ищи по тексту заметок\n\n"
        "📊 *Статистика* — сколько заметок и покупок\n\n"
        "*Категории заметок:*\n"
        "📝 Заметки · 🛒 Покупки · 💼 Работа\n"
        "🏠 Дом · 💡 Идеи · ❤️ Личное"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── ЗАМЕТКИ ──────────────────────────────────────────────────────────────────
async def show_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    notes = get_notes(ctx)
    text = f"📝 *Ваши заметки* ({len(notes)} шт\\.):\n\n"

    if not notes:
        text += "_Заметок пока нет\\. Нажмите ➕ чтобы добавить\\._"
    else:
        # Группируем по категориям
        by_cat = {}
        for nid, note in notes.items():
            cat = note.get("category", "📝")
            by_cat.setdefault(cat, []).append((nid, note))

        for cat_emoji, items in by_cat.items():
            cat_name = NOTE_CATEGORIES.get(cat_emoji, "Прочее")
            text += f"\n*{cat_emoji} {cat_name}* \\({len(items)}\\):\n"
            for nid, note in items[-5:]:
                title = note.get("title", "Без названия")
                title_esc = title.replace(".", "\\.").replace("-", "\\-").replace("!", "\\!")[:30]
                date  = fmt_date(note.get("date", ""))
                text += f"  • {title_esc} _\\({date}\\)_\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2",
            reply_markup=notes_keyboard(notes)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2",
            reply_markup=notes_keyboard(notes)
        )


async def add_note_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 *Новая заметка*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=category_keyboard(),
    )
    return STATE_NOTE_TITLE


async def select_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split(":")[1]
    ctx.user_data["new_note_cat"] = cat
    cat_name = NOTE_CATEGORIES.get(cat, "Заметка")
    await query.edit_message_text(
        f"*{cat} {cat_name}*\n\nВведите *заголовок* заметки:",
        parse_mode="Markdown",
    )
    return STATE_NOTE_TITLE


async def note_title_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if len(title) > 100:
        await update.message.reply_text("❌ Заголовок слишком длинный (макс. 100 символов)\\.", parse_mode="MarkdownV2")
        return STATE_NOTE_TITLE

    ctx.user_data["new_note_title"] = title
    await update.message.reply_text(
        f"✅ Заголовок: *{title}*\n\nТеперь введите *текст* заметки:",
        parse_mode="Markdown",
    )
    return STATE_NOTE_TEXT


async def note_text_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    nid  = note_id()
    notes = get_notes(ctx)
    notes[nid] = {
        "title":    ctx.user_data.get("new_note_title", "Без названия"),
        "text":     text,
        "category": ctx.user_data.get("new_note_cat", "📝"),
        "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    cat   = ctx.user_data.get("new_note_cat", "📝")
    title = ctx.user_data.get("new_note_title", "")

    await update.message.reply_text(
        f"✅ *Заметка сохранена\\!*\n\n"
        f"{cat} *{title}*\n\n"
        f"_{text[:100]}{'\\.\\.\\.' if len(text) > 100 else ''}_",
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
        await query.edit_message_text("❌ Заметка не найдена.")
        return

    cat   = note.get("category", "📝")
    title = note.get("title", "Без названия")
    text  = note.get("text", "")
    date  = fmt_date(note.get("date", ""))

    # Экранируем для MarkdownV2
    def esc(s):
        for c in r"_.!*[]()~`>#+-=|{}":
            s = s.replace(c, f"\\{c}")
        return s

    msg = (
        f"{cat} *{esc(title)}*\n"
        f"_📅 {esc(date)}_\n\n"
        f"{esc(text)}"
    )
    await query.edit_message_text(
        msg, parse_mode="MarkdownV2",
        reply_markup=note_view_keyboard(nid)
    )


async def delete_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nid   = query.data.split(":")[1]
    notes = get_notes(ctx)
    title = notes.pop(nid, {}).get("title", "заметка")
    await query.answer(f"🗑 «{title}» удалена", show_alert=False)
    await show_notes(update, ctx)


async def clear_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["notes"] = {}
    await query.edit_message_text(
        "🗑 Все заметки удалены\\.", parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Добавить заметку", callback_data="add_note")
        ]])
    )


# ─── СПИСОК ПОКУПОК ───────────────────────────────────────────────────────────
async def show_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = get_shop_list(ctx)
    total   = len(shop)
    checked = sum(1 for i in shop if i.get("checked"))

    text = f"🛒 *Список покупок* \\({checked}/{total}\\)\n\n"

    if not shop:
        text += "_Список пуст\\. Нажмите ➕ чтобы добавить товар\\._"
    else:
        for item in shop:
            icon = "✅" if item.get("checked") else "⬜"
            name = item.get("name", "")
            qty  = item.get("qty", "")
            name_esc = name.replace(".", "\\.").replace("-", "\\-")
            line = f"{icon} {name_esc}"
            if qty:
                qty_esc = qty.replace(".", "\\.").replace("-", "\\-")
                line += f" — _{qty_esc}_"
            text += line + "\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2",
            reply_markup=shop_keyboard(shop)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2",
            reply_markup=shop_keyboard(shop)
        )


async def add_item_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛒 *Добавить товар*\n\n"
        "Введите название товара:\n"
        "_(или название и количество через запятую, например: Молоко, 2л)_",
        parse_mode="Markdown",
    )
    return STATE_ADD_SHOP_ITEM


async def item_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    shop = get_shop_list(ctx)

    # Парсим несколько товаров (каждый с новой строки)
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
        f"✅ Добавлено: *{names}*",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

    # Показываем обновлённый список
    await update.message.reply_text(
        f"🛒 Список обновлён\\!",
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
    await query.answer()
    idx  = int(query.data.split(":")[1])
    shop = get_shop_list(ctx)
    if 0 <= idx < len(shop):
        name = shop.pop(idx).get("name", "товар")
        await query.answer(f"🗑 «{name}» удалён", show_alert=False)
    await show_shop(update, ctx)


async def clear_checked(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop = get_shop_list(ctx)
    ctx.user_data["shop_list"] = [i for i in shop if not i.get("checked")]
    await show_shop(update, ctx)


async def clear_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["shop_list"] = []
    await show_shop(update, ctx)


# ─── ПОИСК ────────────────────────────────────────────────────────────────────
async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *Поиск по заметкам*\n\nВведите текст для поиска:",
        parse_mode="Markdown",
    )
    ctx.user_data["searching"] = True


async def do_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("searching"):
        return await text_router(update, ctx)

    ctx.user_data["searching"] = False
    query = update.message.text.strip().lower()
    notes = get_notes(ctx)

    results = []
    for nid, note in notes.items():
        title = note.get("title", "").lower()
        text  = note.get("text", "").lower()
        if query in title or query in text:
            results.append((nid, note))

    if not results:
        await update.message.reply_text(
            f"🔍 По запросу *«{query}»* ничего не найдено\\.",
            parse_mode="MarkdownV2",
            reply_markup=main_keyboard(),
        )
        return

    text_out = f"🔍 Найдено *{len(results)}* заметок:\n\n"
    for nid, note in results:
        cat   = note.get("category", "📝")
        title = note.get("title", "")
        snippet = note.get("text", "")[:50]
        def esc(s):
            for c in r"_.!*[]()~`>#+-=|{}":
                s = s.replace(c, f"\\{c}")
            return s
        text_out += f"{cat} *{esc(title)}*\n_{esc(snippet)}\\.\\.\\._\n\n"

    await update.message.reply_text(
        text_out, parse_mode="MarkdownV2",
        reply_markup=main_keyboard(),
    )


# ─── СТАТИСТИКА ───────────────────────────────────────────────────────────────
async def show_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    notes = get_notes(ctx)
    shop  = get_shop_list(ctx)

    # По категориям
    by_cat = {}
    for note in notes.values():
        cat = note.get("category", "📝")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    checked = sum(1 for i in shop if i.get("checked"))

    text = "📊 *Статистика*\n\n"
    text += f"📝 Всего заметок: *{len(notes)}*\n"

    if by_cat:
        text += "\n*По категориям:*\n"
        for cat, count in by_cat.items():
            name = NOTE_CATEGORIES.get(cat, "Прочее")
            text += f"  {cat} {name}: *{count}*\n"

    text += f"\n🛒 Товаров в списке: *{len(shop)}*\n"
    text += f"  ✅ Куплено: *{checked}*\n"
    text += f"  ⬜ Осталось: *{len(shop) - checked}*\n"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


# ─── РОУТЕР ───────────────────────────────────────────────────────────────────
async def text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📝 Заметки":
        await show_notes(update, ctx)
    elif text == "🛒 Список покупок":
        await show_shop(update, ctx)
    elif text == "🔍 Поиск":
        await search_start(update, ctx)
    elif text == "📊 Статистика":
        await show_stats(update, ctx)
    elif text == "❓ Помощь":
        await cmd_help(update, ctx)
    else:
        await do_search(update, ctx)


async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    if data == "back":
        await query.answer()
        await query.edit_message_text(
            "Выберите раздел 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Заметки",        callback_data="show_notes")],
                [InlineKeyboardButton("🛒 Список покупок", callback_data="show_shop")],
            ])
        )
    elif data == "show_notes":
        await show_notes(update, ctx)
    elif data == "show_shop":
        await show_shop(update, ctx)
    elif data.startswith("view_note:"):
        await view_note(update, ctx)
    elif data.startswith("del_note:"):
        await delete_note(update, ctx)
    elif data == "clear_notes":
        await clear_notes(update, ctx)
    elif data.startswith("toggle:"):
        await toggle_item(update, ctx)
    elif data.startswith("del_item:"):
        await delete_item(update, ctx)
    elif data == "clear_checked":
        await clear_checked(update, ctx)
    elif data == "clear_shop":
        await clear_shop(update, ctx)
    elif data == "cancel":
        await query.answer()
        await query.edit_message_text("❌ Отменено.")


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для заметок
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

    # ConversationHandler для покупок
    shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ad
