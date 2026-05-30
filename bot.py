import telebot
import random
import json
import os
import threading
import time
from datetime import datetime

# --- НАСТРОЙКИ ---
TOKEN = '8615226801:AAGNKoP9MVZL8yI_Gi36SGA68KvPtrTCzZc'  # Замените на токен вашего бота
bot = telebot.TeleBot(TOKEN)
ADMIN_IDS = [7857446636]  # Замените на ваш Telegram ID

# --- ФАЙЛЫ ДЛЯ СОХРАНЕНИЯ ---
USERS_FILE = 'users.txt'
PROMO_FILE = 'promocodes.txt'
STATS_FILE = 'stats.txt'

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
users = {}
promocodes = {}
stats = {"total_users": 0, "total_games_played": 0, "total_bets": 0, "total_won": 0}
rocket_games = {}
rocket_stop_events = {}  # События для остановки потоков

# --- ЗАГРУЗКА ДАННЫХ ---
def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}

def load_promocodes():
    global promocodes
    if os.path.exists(PROMO_FILE):
        with open(PROMO_FILE, 'r', encoding='utf-8') as f:
            promocodes = json.load(f)
    else:
        promocodes = {}

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    else:
        stats = {"total_users": 0, "total_games_played": 0, "total_bets": 0, "total_won": 0}

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_promocodes():
    with open(PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=2)

def save_stats():
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

# --- РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ ---
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

# --- ОБНОВЛЕНИЕ БАЛАНСА ---
def update_balance(user_id, amount):
    if str(user_id) in users:
        users[str(user_id)]["balance"] += amount
        save_users()
        return True
    return False

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_games = telebot.types.KeyboardButton('🎮 ИГРЫ')
    btn_profile = telebot.types.KeyboardButton('👤 ПРОФИЛЬ')
    btn_promo = telebot.types.KeyboardButton('🎁 ПРОМОКОДЫ')
    keyboard.add(btn_games, btn_profile, btn_promo)
    return keyboard

def games_menu_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_rocket = telebot.types.KeyboardButton('🚀 РАКЕТА')
    btn_basketball = telebot.types.KeyboardButton('🏀 БАСКЕТБОЛ')
    btn_back = telebot.types.KeyboardButton('⬅️ НАЗАД')
    keyboard.add(btn_rocket, btn_basketball, btn_back)
    return keyboard

# --- ИГРА РАКЕТА ---
def start_rocket_game(message):
    user_id = message.from_user.id
    if user_id in rocket_games:
        bot.send_message(message.chat.id, "❌ У вас уже активна игра в Ракету!")
        return
    
    msg = bot.send_message(message.chat.id, "🚀 Введите сумму ставки для игры РАКЕТА:")
    bot.register_next_step_handler(msg, process_rocket_bet)

def process_rocket_bet(message):
    user_id = message.from_user.id
    try:
        bet = float(message.text)
        if bet <= 0:
            raise ValueError
        if users[str(user_id)]["balance"] < bet:
            bot.send_message(message.chat.id, "❌ Недостаточно средств!", reply_markup=games_menu_keyboard())
            return
        
        update_balance(user_id, -bet)
        
        keyboard = telebot.types.InlineKeyboardMarkup()
        stop_btn = telebot.types.InlineKeyboardButton("🛑 ОСТАНОВИТЬ", callback_data=f"rocket_stop_{user_id}")
        keyboard.add(stop_btn)
        
        msg = bot.send_message(message.chat.id, f"🚀 РАКЕТА ВЗЛЕТАЕТ!\n💰 Ставка: {bet:.2f}\n📈 Множитель: 1.00x\n💎 Возможный выигрыш: {bet:.2f}", reply_markup=keyboard)
        
        # Создаем событие для остановки
        stop_event = threading.Event()
        rocket_stop_events[user_id] = stop_event
        
        rocket_games[user_id] = {
            "active": True,
            "bet": bet,
            "multiplier": 1.0,
            "stop_called": False,
            "chat_id": message.chat.id,
            "message_id": msg.message_id,
            "stop_event": stop_event
        }
        
        def rocket_thread():
            multiplier = 1.0
            crashed = False
            
            while not stop_event.is_set():
                time.sleep(0.3)
                
                if stop_event.is_set():
                    break
                
                multiplier += 0.1
                rocket_games[user_id]["multiplier"] = multiplier
                win = bet * multiplier
                
                # Проверка на краш (40% шанс)
                if random.random() < 0.4 and multiplier > 1.5 and not crashed:
                    crashed = True
                    rocket_games[user_id]["active"] = False
                    
                    try:
                        bot.edit_message_text(f"💥 РАКЕТА ВЗОРВАЛАСЬ! 💥\n📈 Множитель был: {multiplier:.2f}x\n💰 Вы потеряли ставку: {bet:.2f}", 
                                            message.chat.id, rocket_games[user_id]["message_id"])
                    except:
                        pass
                    
                    # Удаляем игру
                    if user_id in rocket_games:
                        del rocket_games[user_id]
                    if user_id in rocket_stop_events:
                        del rocket_stop_events[user_id]
                    break
                
                # Обновляем сообщение, если игра еще активна
                if not crashed and user_id in rocket_games and rocket_games[user_id]["active"]:
                    try:
                        bot.edit_message_text(f"🚀 РАКЕТА ВЗЛЕТАЕТ!\n💰 Ставка: {bet:.2f}\n📈 Множитель: {multiplier:.2f}x\n💎 Возможный выигрыш: {win:.2f}", 
                                             message.chat.id, rocket_games[user_id]["message_id"], reply_markup=keyboard)
                    except:
                        pass
        
        thread = threading.Thread(target=rocket_thread, daemon=True)
        thread.start()
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму!", reply_markup=games_menu_keyboard())

# --- ИГРА БАСКЕТБОЛ ---
def start_basketball_game(message):
    bot.send_message(message.chat.id, "🏀 БАСКЕТБОЛ 🏀\nВведите сумму ставки:")
    bot.register_next_step_handler(message, process_basketball_bet)

def process_basketball_bet(message):
    user_id = message.from_user.id
    try:
        bet = float(message.text)
        if bet <= 0:
            raise ValueError
        if users[str(user_id)]["balance"] < bet:
            bot.send_message(message.chat.id, "❌ Недостаточно средств!", reply_markup=games_menu_keyboard())
            return
        
        update_balance(user_id, -bet)
        
        bot.send_chat_action(message.chat.id, 'typing')
        time.sleep(1)
        
        hoop_msg = bot.send_message(message.chat.id, "🏀 БРОСОК! 🏀\n\n")
        
        time.sleep(1.5)
        
        stats["total_games_played"] += 1
        stats["total_bets"] += bet
        
        if random.random() < 0.5:
            win = bet * 2
            update_balance(user_id, win)
            stats["total_won"] += win
            save_stats()
            
            bot.edit_message_text(
                f"🏀 БРОСОК! 🏀\n\n"
                f"🎯 🗑️✨ ПОПАДАНИЕ! ✨🗑️ 🎯\n\n"
                f"💰 Вы выиграли: {win:.2f}\n"
                f"💎 Ставка удвоена!\n"
                f"🏆 Новый баланс: {users[str(user_id)]['balance']:.2f}",
                message.chat.id, hoop_msg.message_id
            )
        else:
            save_stats()
            
            bot.edit_message_text(
                f"🏀 БРОСОК! 🏀\n\n"
                f"❌ 🔄 МИМО! 🔄 ❌\n\n"
                f"💰 Вы потеряли: {bet:.2f}\n"
                f"💔 Попробуйте еще раз!\n"
                f"🏆 Новый баланс: {users[str(user_id)]['balance']:.2f}",
                message.chat.id, hoop_msg.message_id
            )
        
        keyboard = telebot.types.InlineKeyboardMarkup()
        play_again = telebot.types.InlineKeyboardButton("🎮 Играть еще", callback_data="basketball_again")
        keyboard.add(play_again)
        
        bot.send_message(message.chat.id, "Хотите сыграть еще раз?", reply_markup=keyboard)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму!", reply_markup=games_menu_keyboard())

# --- ПРОФИЛЬ ---
def show_profile(message):
    user_id = str(message.from_user.id)
    if user_id in users:
        user = users[user_id]
        profile_text = f"""
👤 **ПРОФИЛЬ**
━━━━━━━━━━━━━━━
📝 Ник: {user['nick']}
💰 Баланс: {user['balance']:.2f}
📅 Регистрация: {user['register_date']}
🆔 ID: {message.from_user.id}
━━━━━━━━━━━━━━━
        """
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
    else:
        register_user(message.from_user.id, message.from_user.username)
        show_profile(message)

# --- ПРОМОКОДЫ ---
def use_promocode(message):
    bot.send_message(message.chat.id, "🎁 Введите промокод:")
    bot.register_next_step_handler(message, process_promocode)

def process_promocode(message):
    user_id = str(message.from_user.id)
    code = message.text.upper()
    
    if code in promocodes:
        promo = promocodes[code]
        if promo["uses_left"] != 0 and promo["uses_left"] > 0:
            promo["uses_left"] -= 1
            update_balance(user_id, promo["money"])
            save_promocodes()
            bot.send_message(message.chat.id, f"✅ Промокод активирован!\n💰 +{promo['money']:.2f} к балансу!", reply_markup=main_menu_keyboard())
        elif promo["uses_left"] == -1:
            update_balance(user_id, promo["money"])
            bot.send_message(message.chat.id, f"✅ Промокод активирован!\n💰 +{promo['money']:.2f} к балансу!", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Промокод уже использован!", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Неверный промокод!", reply_markup=main_menu_keyboard())

# --- АДМИН КОМАНДЫ ---
@bot.message_handler(commands=['createpromo'])
def create_promo(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Доступ только для админов!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.send_message(message.chat.id, "❌ Использование: /createpromo (код) (деньги) (кол-во использований)\n0 = бесконечно")
            return
        
        code = parts[1].upper()
        money = float(parts[2])
        uses = int(parts[3])
        
        promocodes[code] = {"money": money, "uses_left": uses if uses != 0 else -1}
        save_promocodes()
        bot.send_message(message.chat.id, f"✅ Промокод {code} создан!\n💰 {money:.2f} | 🔄 {'Бесконечно' if uses == 0 else uses}")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Проверьте формат: /createpromo CODE 1000 5")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Доступ только для админов!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Использование: /ban @username")
            return
        
        username = parts[1].replace('@', '')
        found = False
        for uid, data in users.items():
            if data['nick'] == username or uid == username:
                users[uid]['balance'] = -999999
                save_users()
                bot.send_message(message.chat.id, f"✅ Пользователь {username} забанен!")
                found = True
                break
        
        if not found:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка!")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Доступ только для админов!")
        return
    
    stats_text = f"""
📊 **СТАТИСТИКА БОТА**
━━━━━━━━━━━━━━━
👥 Всего пользователей: {stats['total_users']}
🎮 Сыграно игр: {stats['total_games_played']}
💰 Общая сумма ставок: {stats['total_bets']:.2f}
🏆 Выиграно всего: {stats['total_won']:.2f}
📈 Профит казино: {stats['total_bets'] - stats['total_won']:.2f}
━━━━━━━━━━━━━━━
    """
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['sendmoney'])
def send_money(message):
    """Админ команда для выдачи денег пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Доступ только для админов!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Использование: /sendmoney (user_id) (сумма)")
            return
        
        user_id = parts[1]
        amount = float(parts[2])
        
        if user_id in users:
            update_balance(user_id, amount)
            bot.send_message(message.chat.id, f"✅ Пользователю {users[user_id]['nick']} выдано {amount:.2f}!\n💰 Новый баланс: {users[user_id]['balance']:.2f}")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка!")

@bot.message_handler(commands=['sms'])
def send_sms_to_all(message):
    """Команда для рассылки сообщений всем пользователям"""
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Доступ только для админов!")
        return
    
    try:
        # Получаем текст сообщения после команды /sms
        sms_text = message.text.replace('/sms', '').strip()
        
        if not sms_text:
            bot.send_message(message.chat.id, "❌ Использование: /sms (текст сообщения)\n\nПример: /sms Внимание! Технические работы через 1 час!")
            return
        
        # Подтверждение перед отправкой
        keyboard = telebot.types.InlineKeyboardMarkup()
        confirm_btn = telebot.types.InlineKeyboardButton("✅ ДА, ОТПРАВИТЬ", callback_data=f"confirm_sms_{sms_text}")
        cancel_btn = telebot.types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_sms")
        keyboard.add(confirm_btn, cancel_btn)
        
        preview_text = sms_text[:200] + "..." if len(sms_text) > 200 else sms_text
        bot.send_message(message.chat.id, 
                        f"📨 **ПОДТВЕРЖДЕНИЕ РАССЫЛКИ**\n\n"
                        f"📊 Будет отправлено: {len(users)} пользователям\n"
                        f"📝 Текст сообщения:\n{preview_text}\n\n"
                        f"Отправить?", 
                        parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

def send_broadcast(sms_text, admin_id):
    """Функция для отправки сообщений всем пользователям"""
    success_count = 0
    fail_count = 0
    
    # Отправляем сообщение админу о начале рассылки
    bot.send_message(admin_id, "📨 Начинаю рассылку...")
    
    for user_id in users.keys():
        try:
            # Форматируем сообщение с красивым оформлением
            broadcast_msg = f"""
📢 **МАССОВОЕ УВЕДОМЛЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━

{sms_text}

━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
            """
            bot.send_message(int(user_id), broadcast_msg, parse_mode='Markdown')
            success_count += 1
            time.sleep(0.05)  # Небольшая задержка чтобы не спамить
        except:
            fail_count += 1
    
    # Отправляем отчет админу
    report = f"""
✅ **РАССЫЛКА ЗАВЕРШЕНА**
━━━━━━━━━━━━━━━
✅ Успешно доставлено: {success_count}
❌ Не доставлено: {fail_count}
📊 Всего пользователей: {len(users)}
━━━━━━━━━━━━━━━
    """
    bot.send_message(admin_id, report, parse_mode='Markdown')

# --- ОБРАБОТКА КНОПОК ---
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username)
    
    if message.text == '🎮 ИГРЫ':
        bot.send_message(message.chat.id, "🎮 Выберите игру:", reply_markup=games_menu_keyboard())
    
    elif message.text == '👤 ПРОФИЛЬ':
        show_profile(message)
    
    elif message.text == '🎁 ПРОМОКОДЫ':
        use_promocode(message)
    
    elif message.text == '🚀 РАКЕТА':
        start_rocket_game(message)
    
    elif message.text == '🏀 БАСКЕТБОЛ':
        start_basketball_game(message)
    
    elif message.text == '⬅️ НАЗАД':
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard())
    
    else:
        bot.send_message(message.chat.id, "Используйте кнопки меню!", reply_markup=main_menu_keyboard())

# --- ОБРАБОТКА INLINE КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # Обработка остановки ракеты
    if call.data.startswith('rocket_stop'):
        user_id = int(call.data.split('_')[2])
        
        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Это не ваша игра!", show_alert=True)
            return
        
        # Останавливаем игру
        if user_id in rocket_games and user_id in rocket_stop_events:
            # Сигнал остановки потока
            rocket_stop_events[user_id].set()
            
            game = rocket_games[user_id]
            
            if not game["stop_called"]:
                game["stop_called"] = True
                winnings = game["bet"] * game["multiplier"]
                update_balance(user_id, winnings)
                
                stats["total_games_played"] += 1
                stats["total_bets"] += game["bet"]
                stats["total_won"] += winnings
                save_stats()
                
                try:
                    bot.edit_message_text(f"🛑 ВЫ ОСТАНОВИЛИ РАКЕТУ! 🛑\n💰 Ставка: {game['bet']:.2f}\n📈 Множитель: {game['multiplier']:.2f}x\n🎉 ВЫИГРЫШ: {winnings:.2f}\n💰 Новый баланс: {users[str(user_id)]['balance']:.2f}",
                                         call.message.chat.id, call.message.message_id)
                except:
                    pass
            
            # Удаляем игру
            if user_id in rocket_games:
                del rocket_games[user_id]
            if user_id in rocket_stop_events:
                del rocket_stop_events[user_id]
            
            bot.answer_callback_query(call.id, "✅ Игра остановлена! Выигрыш зачислен!")
        else:
            bot.answer_callback_query(call.id, "❌ Игра уже завершена!", show_alert=True)
    
    # Обработка баскетбол "играть еще"
    elif call.data == 'basketball_again':
        bot.answer_callback_query(call.id)
        start_basketball_game(call.message)
    
    # Обработка подтверждения рассылки
    elif call.data.startswith('confirm_sms_'):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Доступ только для админов!", show_alert=True)
            return
        
        sms_text = call.data.replace('confirm_sms_', '')
        bot.answer_callback_query(call.id, "✅ Рассылка начата!")
        bot.edit_message_text("📨 Рассылка запущена... Ожидайте отчет.", call.message.chat.id, call.message.message_id)
        
        # Запускаем рассылку в отдельном потоке
        thread = threading.Thread(target=send_broadcast, args=(sms_text, call.from_user.id))
        thread.daemon = True
        thread.start()
    
    elif call.data == 'cancel_sms':
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ Доступ только для админов!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "❌ Рассылка отменена")
        bot.edit_message_text("❌ Рассылка отменена администратором.", call.message.chat.id, call.message.message_id)

# --- КОМАНДА /start ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username)
    bot.send_message(message.chat.id, 
                     f"🎮 Добро пожаловать в игровой бот, {message.from_user.first_name}!\n\n"
                     f"💰 Ваш начальный баланс: 1000\n\n"
                     f"Доступные игры:\n"
                     f"🚀 РАКЕТА - взлетай и забирай выигрыш вовремя!\n"
                     f"🏀 БАСКЕТБОЛ - бот сам бросает мяч, попади в кольцо!\n\n"
                     f"Используйте кнопки меню для навигации.",
                     reply_markup=main_menu_keyboard())

# --- ЗАПУСК ---
if __name__ == "__main__":
    load_users()
    load_promocodes()
    load_stats()
    print("✅ Бот запущен!")
    print(f"👥 Загружено пользователей: {len(users)}")
    print(f"🎁 Загружено промокодов: {len(promocodes)}")
    print(f"👑 Админы: {ADMIN_IDS}")
    bot.polling(none_stop=True)