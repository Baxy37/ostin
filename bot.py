import asyncio
import logging
import os
import sqlite3
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import uvicorn

# ============ ЗАГРУЗКА КОНФИГУРАЦИИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "8911456302:AAFXu58SGEeCKZED7CiV5TCPvNADQ4pJX6M")

LINKS = {
    "link1": "https://telegram.me/portals/market?startapp=p0yi8t-ref_gameUmRk-to_games",
    "link2": "https://telegram.me/portals/market?startapp=p0yi8t"
}

COURSE_FILE = os.path.join(os.path.dirname(__file__), "ostin_plug_nft_guide.pdf")
DB_PATH = "/tmp/users.db"

# ============ НАСТРОЙКА ЛОГГИРОВАНИЯ ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============ ИНИЦИАЛИЗАЦИЯ ============
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
router = Router()
app = FastAPI()

# ============ РАБОТА С БАЗОЙ ДАННЫХ ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            link1_clicked INTEGER DEFAULT 0,
            link2_clicked INTEGER DEFAULT 0,
            course_sent INTEGER DEFAULT 0,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT link1_clicked, link2_clicked, course_sent FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "link1": bool(row[0]),
                "link2": bool(row[1]),
                "course_sent": bool(row[2])
            }
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
    return None

def create_user(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка создания пользователя {user_id}: {e}")

def mark_link_clicked(user_id: int, link_num: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        column = "link1_clicked" if link_num == 1 else "link2_clicked"
        cursor.execute(
            f"UPDATE users SET {column} = 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка отметки ссылки для {user_id}: {e}")

def mark_course_sent(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET course_sent = 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка отметки курса для {user_id}: {e}")

def reset_user(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET link1_clicked = 0, link2_clicked = 0, course_sent = 0 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сброса для {user_id}: {e}")

# ============ КЛАВИАТУРЫ ============
def get_start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 Платформа 1 (обязательно)",
                url=LINKS["link1"]
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 Платформа 2 (обязательно)",
                url=LINKS["link2"]
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Я перешёл по обеим ссылкам!",
                callback_data="check_links"
            )
        ]
    ])

def get_course_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📖 Скачать 1 часть курса",
                callback_data="get_part1"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔜 2 часть (скоро)",
                callback_data="part2_soon"
            )
        ]
    ])

def get_retry_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Проверить снова",
                callback_data="check_links"
            )
        ]
    ])

# ============ ОБРАБОТЧИКИ КОМАНД ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    
    logger.info(f"Пользователь @{username} (ID: {user_id}) запустил бота")
    
    create_user(user_id)
    user_data = get_user(user_id)
    
    if user_data and user_data["course_sent"]:
        await message.answer(
            "📚 <b>Вы уже получили доступ к курсу!</b>\n\n"
            "Если хотите перечитать или скачать заново, нажмите кнопку ниже:",
            reply_markup=get_course_keyboard()
        )
        return
    
    welcome_text = (
        "🔥 <b>Приветствую тебя на моём бесплатном курсе по заработку на NFT-подарках!</b>\n\n"
        "Этот курс создан для тех, кто хочет научиться зарабатывать реальные деньги "
        "на арбитраже NFT в Telegram. Я вложил в него свой многолетний опыт, "
        "чтобы ты мог начать с нуля и уже через неделю видеть первые результаты.\n\n"
        "📊 <i>Что ты получишь в этом курсе:</i>\n"
        "• Пошаговые стратегии заработка\n"
        "• Актуальные данные по рынку на 2026 год\n"
        "• Сравнение всех площадок и комиссий\n"
        "• Реальные примеры с расчётами прибыли\n\n"
        "❗️ <b>Важное условие:</b>\n"
        "Чтобы получить доступ к курсу, нужно перейти по <b>ДВУМ</b> ссылкам ниже. "
        "Это моя партнёрская программа — так мы с тобой сможем работать дальше, "
        "и я буду давать тебе ещё больше эксклюзивных материалов.\n\n"
        "👇 <b>Переходи по ссылкам и возвращайся сюда!</b>"
    )
    
    await message.answer(welcome_text, reply_markup=get_start_keyboard())

@router.callback_query(F.data == "check_links")
async def check_links(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "без username"
    
    logger.info(f"Пользователь @{username} (ID: {user_id}) проверяет ссылки")
    
    user_data = get_user(user_id)
    
    if not user_data:
        await callback.answer("Ошибка! Перезапустите бота командой /start", show_alert=True)
        return
    
    link1 = user_data["link1"]
    link2 = user_data["link2"]
    
    if not link1 or not link2:
        missing = []
        if not link1:
            missing.append("🔗 Ссылка 1")
        if not link2:
            missing.append("🔗 Ссылка 2")
        
        missing_text = "\n".join(missing)
        
        await callback.answer(
            "❌ Ты не перешёл по всем ссылкам!\n\n"
            f"Не открыты:\n{missing_text}\n\n"
            "Перейди сначала по ссылкам, потом нажми проверку.",
            show_alert=True
        )
        
        await callback.message.answer(
            "⚠️ <b>Внимание!</b>\n\n"
            f"Ты ещё не перешёл по этим ссылкам:\n{missing_text}\n\n"
            "Перейди по ним и нажми кнопку ниже.",
            reply_markup=get_retry_keyboard()
        )
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ <b>Отлично! Ты выполнил все условия!</b>\n\n"
        "Теперь тебе доступен полный гайд по заработку на NFT-подарках.\n"
        "Нажми кнопку ниже, чтобы скачать 1 часть курса 👇",
        reply_markup=get_course_keyboard()
    )
    await callback.answer("🎉 Доступ открыт!")

@router.callback_query(F.data == "get_part1")
async def send_part1(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "без username"
    
    logger.info(f"Пользователь @{username} (ID: {user_id}) запросил 1 часть курса")
    
    user_data = get_user(user_id)
    
    if not user_data or not user_data["link1"] or not user_data["link2"]:
        await callback.answer(
            "❌ Сначала перейди по ссылкам! Используй /start",
            show_alert=True
        )
        return
    
    if not os.path.exists(COURSE_FILE):
        logger.error(f"Файл {COURSE_FILE} не найден!")
        await callback.answer(
            "⚠️ Файл курса временно недоступен. Попробуйте позже.",
            show_alert=True
        )
        return
    
    mark_course_sent(user_id)
    
    try:
        file = FSInputFile(COURSE_FILE)
        await callback.message.answer_document(
            file,
            caption=(
                "📘 <b>Часть 1 — Полный гайд по заработку на NFT-подарках</b>\n\n"
                "В этом файле ты найдёшь:\n"
                "• 🔄 Стратегии арбитража (флип, охота за недооценёнными активами)\n"
                "• 📊 Сравнение всех площадок (Portals, Tonnel, MRKT, xGift)\n"
                "• 📈 Пошаговые схемы с реальными расчётами прибыли\n"
                "• 💰 Инструменты и комиссии в одной удобной таблице\n"
                "• 🎯 Советы от опытных трейдеров\n\n"
                "📖 Изучай, применяй на практике и делись результатами!\n\n"
                "🔜 <b>2 часть курса выйдет совсем скоро — следи за обновлениями!</b>\n\n"
                "💪 Удачи в торговле!"
            )
        )
        await callback.answer("📄 Курс отправлен! Удачи в изучении!")
        
        await callback.message.answer(
            "💎 <b>Ты сделал первый шаг к финансовой независимости!</b>\n\n"
            "Запомни: 90% успеха — это дисциплина и постоянный анализ рынка.\n"
            "Используй все стратегии из гайда, не бойся экспериментировать,\n"
            "но всегда помни о рисках.\n\n"
            "🚀 Увидимся во 2 части курса!"
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки файла {user_id}: {e}")
        await callback.answer("⚠️ Ошибка отправки. Попробуйте позже.", show_alert=True)

@router.callback_query(F.data == "part2_soon")
async def part2_soon(callback: CallbackQuery):
    await callback.answer(
        "🔜 2 часть в разработке! Выходит в ближайшее время.",
        show_alert=True
    )
    
    await callback.message.answer(
        "📢 <b>Скоро выйдет 2 часть курса!</b>\n\n"
        "В ней я расскажу:\n"
        "• Продвинутые стратегии арбитража\n"
        "• Работа с маркет-мейкингом\n"
        "• Как использовать ботов для автоматизации\n"
        "• И многие другие фишки!\n\n"
        "Не переключайся! 🔥"
    )

# ============ НАСТРОЙКА WEBHOOK ============
@app.on_event("startup")
async def on_startup():
    try:
        init_db()
        logger.info("База данных инициализирована")
        
        webhook_url = os.getenv("RENDER_EXTERNAL_URL", "https://ostin.onrender.com")
        webhook_path = f"/webhook/{BOT_TOKEN}"
        webhook_url_full = f"{webhook_url}{webhook_path}"
        
        await bot.set_webhook(url=webhook_url_full, drop_pending_updates=True)
        logger.info(f"Webhook установлен: {webhook_url_full}")
        
        dp.include_router(router)
        
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)
        
    except Exception as e:
        logger.error(f"Ошибка при старте: {e}")

# ============ ПРАВИЛЬНЫЙ ОБРАБОТЧИК ЗАВЕРШЕНИЯ ============
async def on_shutdown():
    logger.info("Бот завершает работу...")
    await bot.session.close()

app.add_event_handler("shutdown", on_shutdown)

# ============ ЗАПУСК ============
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
