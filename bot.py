import os
import threading
import time
import random
import json
from datetime import datetime
from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.environ.get('8622203700:AAEf0UhiSdTdsdadiFX9QFHxyVcVP9hEbM4')
if not TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден в переменных окружения!")
    exit(1)

ADMIN_IDS = [7857446636]  # ЗАМЕНИТЕ НА ВАШ ID

# ========== ФАЙЛЫ ==========
USERS_FILE = 'users.txt'
PROMO_FILE = 'promocodes.txt'
STATS_FILE = 'stats.txt'

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
users = {}
promocodes = {}
stats = {"total_users": 0, "total_games_played": 0, "total_bets": 0, "total_won": 0}
rocket_games = {}

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== ЗАГРУЗКА ДАННЫХ ==========
def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_promocodes():
    global promocodes
    if os.path.exists(PROMO_FILE):
        with open(PROMO_FILE, 'r', encoding='utf-8') as f:
            promocodes = json.load(f)
    else:
        promocodes = {}

def save_promocodes():
    with open(PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=2)

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    else:
        stats = {"total_users": 0, "total_games_played": 0, "total_bets": 0, "total_won": 0}

def save_stats():
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def register_user(user_id, username):
    if str(user_id) not in users:
        users[str(user_id)] = {
            "nick": username if username else f"User{user_id}",
            "balance": 1000,
            "register_date": str(datetime.now())
        }
        stats["total_users"] += 1
        save_users()
        save_stats()
        return True
    return False

def update_balance(user_id, amount):
    if str(user_id) in users:
        users[str(user_id)]["balance"] += amount
        save_users()
        return True
    return False

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(KeyboardButton('🎮 ИГРЫ'), KeyboardButton('👤 ПРОФИЛЬ'), KeyboardButton('🎁 ПРОМОКОДЫ'))
    return kb

def games_menu():
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(KeyboardButton('🚀 РАКЕТА'), KeyboardButton('🏀 БАСКЕТБОЛ'), KeyboardButton('⬅️ НАЗАД'))
    return kb

# ========== БАСКЕТБОЛ ==========
@bot.message_handler(func=lambda m: m.text == '🏀 БАСКЕТБОЛ')
def basketball_start(m):
    bot.send_message(m.chat.id, "🏀 Введите сумму ставки:")
    bot.register_next_step_handler(m, basketball_bet)

def basketball_bet(m):
    try:
        bet = float(m.text)
        uid = str(m.from_user.id)
        if users[uid]["balance"] < bet:
            bot.send_message(m.chat.id, "❌ Недостаточно средств!", reply_markup=games_menu())
            return
        update_balance(m.from_user.id, -bet)
        
        bot.send_message(m.chat.id, "🏀 БРОСОК...")
        time.sleep(1)
        
        if random.random() < 0.5:
            win = bet * 2
            update_balance(m.from_user.id, win)
            stats["total_won"] += win
            bot.send_message(m.chat.id, f"🎯 ПОПАДАНИЕ! +{win:.2f}\n💰 Баланс: {users[uid]['balance']:.2f}", reply_markup=games_menu())
        else:
            bot.send_message(m.chat.id, f"❌ МИМО! Потеряно {bet:.2f}\n💰 Баланс: {users[uid]['balance']:.2f}", reply_markup=games_menu())
        
        stats["total_games_played"] += 1
        stats["total_bets"] += bet
        save_stats()
    except:
        bot.send_message(m.chat.id, "❌ Введите число!", reply_markup=games_menu())

# ========== ПРОФИЛЬ ==========
@bot.message_handler(func=lambda m: m.text == '👤 ПРОФИЛЬ')
def profile(m):
    uid = str(m.from_user.id)
    if uid in users:
        u = users[uid]
        bot.send_message(m.chat.id, f"👤 **ПРОФИЛЬ**\n━━━━━━━━━━\n📝 Ник: {u['nick']}\n💰 Баланс: {u['balance']:.2f}\n📅 Регистрация: {u['register_date']}", parse_mode='Markdown', reply_markup=main_menu())

# ========== ПРОМОКОДЫ ==========
@bot.message_handler(func=lambda m: m.text == '🎁 ПРОМОКОДЫ')
def promo_start(m):
    bot.send_message(m.chat.id, "🎁 Введите промокод:")
    bot.register_next_step_handler(m, promo_use)

def promo_use(m):
    code = m.text.upper()
    uid = str(m.from_user.id)
    if code in promocodes:
        p = promocodes[code]
        if p["uses_left"] != 0:
            if p["uses_left"] > 0:
                p["uses_left"] -= 1
            update_balance(m.from_user.id, p["money"])
            save_promocodes()
            bot.send_message(m.chat.id, f"✅ +{p['money']:.2f} к балансу!", reply_markup=main_menu())
        else:
            bot.send_message(m.chat.id, "❌ Промокод использован!", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "❌ Неверный промокод!", reply_markup=main_menu())

# ========== НАЗАД ==========
@bot.message_handler(func=lambda m: m.text == '⬅️ НАЗАД')
def back(m):
    bot.send_message(m.chat.id, "Главное меню:", reply_markup=main_menu())

# ========== ИГРЫ МЕНЮ ==========
@bot.message_handler(func=lambda m: m.text == '🎮 ИГРЫ')
def games(m):
    bot.send_message(m.chat.id, "Выберите игру:", reply_markup=games_menu())

# ========== РАКЕТА ==========
@bot.message_handler(func=lambda m: m.text == '🚀 РАКЕТА')
def rocket_start(m):
    bot.send_message(m.chat.id, "🚀 Введите ставку:")
    bot.register_next_step_handler(m, rocket_bet)

def rocket_bet(m):
    try:
        bet = float(m.text)
        uid = m.from_user.id
        if users[str(uid)]["balance"] < bet:
            bot.send_message(m.chat.id, "❌ Недостаточно средств!", reply_markup=games_menu())
            return
        update_balance(uid, -bet)
        
        msg = bot.send_message(m.chat.id, "🚀 РАКЕТА ВЗЛЕТАЕТ!\n📈 Множитель: 1.00x")
        
        multiplier = 1.0
        crashed = False
        stop_btn = InlineKeyboardMarkup()
        stop_btn.add(InlineKeyboardButton("🛑 ОСТАНОВИТЬ", callback_data=f"stop_{uid}_{bet}"))
        
        for i in range(20):
            time.sleep(0.5)
            multiplier += 0.1
            if random.random() < 0.3 and multiplier > 1.5:
                crashed = True
                bot.edit_message_text(f"💥 ВЗРЫВ! Множитель был: {multiplier:.1f}x\n💰 Потеряно: {bet:.2f}", m.chat.id, msg.message_id)
                break
            bot.edit_message_text(f"🚀 РАКЕТА ВЗЛЕТАЕТ!\n📈 Множитель: {multiplier:.2f}x\n💎 Выигрыш: {bet * multiplier:.2f}", m.chat.id, msg.message_id, reply_markup=stop_btn)
        
        if not crashed:
            winnings = bet * multiplier
            update_balance(uid, winnings)
            bot.edit_message_text(f"🛑 ОСТАНОВЛЕНО! +{winnings:.2f}", m.chat.id, msg.message_id)
        
        stats["total_games_played"] += 1
        stats["total_bets"] += bet
        save_stats()
    except:
        bot.send_message(m.chat.id, "❌ Введите число!", reply_markup=games_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def rocket_stop(call):
    data = call.data.split('_')
    uid = int(data[1])
    if call.from_user.id == uid:
        bot.answer_callback_query(call.id, "✅ Остановлено!")
    else:
        bot.answer_callback_query(call.id, "❌ Не ваша игра!")

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(m):
    register_user(m.from_user.id, m.from_user.username)
    bot.send_message(m.chat.id, f"🎮 Добро пожаловать, {m.from_user.first_name}!\n💰 Баланс: 1000\nИспользуйте кнопки!", reply_markup=main_menu())

# ========== АДМИН КОМАНДЫ ==========
@bot.message_handler(commands=['stats'])
def stats_cmd(m):
    if m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, f"📊 Статистика:\n👥 Пользователей: {stats['total_users']}\n🎮 Игр сыграно: {stats['total_games_played']}\n💰 Ставок: {stats['total_bets']:.2f}\n🏆 Выиграно: {stats['total_won']:.2f}")

@bot.message_handler(commands=['createpromo'])
def create_promo(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = m.text.split()
        code = parts[1].upper()
        money = float(parts[2])
        uses = int(parts[3])
        promocodes[code] = {"money": money, "uses_left": uses if uses != 0 else -1}
        save_promocodes()
        bot.send_message(m.chat.id, f"✅ Промокод {code} создан!")
    except:
        bot.send_message(m.chat.id, "❌ /createpromo CODE 1000 5")

# ========== FLASK ДЛЯ RENDER ==========
@app.route('/')
@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    """Эндпоинт для cron-job.org чтобы держать бота живым"""
    return "I'm alive", 200

def run_bot():
    print("🔄 Загрузка данных...")
    load_users()
    load_promocodes()
    load_stats()
    print(f"✅ Загружено пользователей: {len(users)}")
    print("✅ Бот запущен и слушает сообщения!")
    
    # Сбрасываем вебхук перед запуском
    try:
        bot.remove_webhook()
        print("✅ Вебхук сброшен")
    except Exception as e:
        print(f"⚠️ Ошибка сброса вебхука: {e}")
    
    # Запускаем polling
    bot.infinity_polling(timeout=60, skip_pending=True)

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Запуск Flask сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)