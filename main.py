from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

import time
import requests
import json
import os
TOKEN = os.getenv("TOKEN")

# 👉 ВСТАВЬ СВОЙ TOKEN ОТ BotFather
TOKEN = "8328515279:AAHoa0i2kPAWk52uLlX-reL39Hcin-2Rhh4"

# канал
CHANNEL_ID = "@poputchiki_md"

# 👉 ВСТАВЬ ИМЯ БОТА, КАК В TELEGRAM
BOT_USERNAME = "@poputchiki_md_bot"

# 👉 ВСТАВЬ ССЫЛКУ НА ПОСТ ПРО БЕЗОПАСНОСТЬ В КАНАЛЕ
# например: "https://t.me/poputchiki_md/5"
SAFETY_URL = "https://t.me/poputchiki_md/18"

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# состояние пользователей: chat_id -> {"step": ..., "data": {...}}
STATE = {}


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup)

    requests.post(f"{BASE_URL}/sendMessage", data=data)


def send_to_channel(text):
    resp = requests.post(f"{BASE_URL}/sendMessage", data={
        "chat_id": CHANNEL_ID,
        "text": text
    })
    # на всякий случай можем смотреть ответ:
    print(resp.text)

# клавиатура выбора роли
ROLE_KEYBOARD = {
    "keyboard": [
        [{"text": "🚗 ВОДИТЕЛЬ"}, {"text": "🧍 ПАССАЖИР"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# дата
DATE_KEYBOARD = {
    "keyboard": [
        [{"text": "Сегодня"}, {"text": "Завтра"}],
        [{"text": "Другая дата"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# комментарий
COMMENT_CHOICE_KB = {
    "keyboard": [
        [{"text": "Добавить комментарий"}, {"text": "Без комментария"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# цена
PRICE_MODE_KB = {
    "keyboard": [
        [{"text": "Указать цену"}, {"text": "Цена обсуждается"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# номер авто
PLATE_CHOICE_KB = {
    "keyboard": [
        [{"text": "Добавить номер авто"}, {"text": "Без номера"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# местоположение
LOCATION_KB = {
    "keyboard": [
        [{"text": "Отправить местоположение", "request_location": True}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

REMOVE_KB = {"remove_keyboard": True}


def format_location(message):
    loc = message.get("location")
    if not loc:
        return None
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    return f"https://maps.google.com/?q={lat},{lon}"


def handle_text(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    location_str = format_location(message)

    # START
    if text == "/start":
        STATE[chat_id] = {"step": "role", "data": {}}
        send_message(
            chat_id,
            "Привет! Выберите, кто вы:",
            reply_markup=ROLE_KEYBOARD
        )
        return

    if chat_id not in STATE:
        send_message(chat_id, "Напишите /start, чтобы создать объявление.")
        return

    step = STATE[chat_id]["step"]
    data = STATE[chat_id]["data"]

    # 1) РОЛЬ
    if step == "role":
        if "ВОДИТЕЛЬ" in text.upper():
            data["role"] = "ВОДИТЕЛЬ"
        elif "ПАССАЖИР" in text.upper():
            data["role"] = "ПАССАЖИР"
        else:
            send_message(chat_id, "Пожалуйста, выберите кнопку ВОДИТЕЛЬ или ПАССАЖИР.", reply_markup=ROLE_KEYBOARD)
            return

        STATE[chat_id]["step"] = "name"
        send_message(chat_id, "Как вас зовут? Напишите имя или имя и фамилию.", reply_markup=REMOVE_KB)

    # 2) ИМЯ
    elif step == "name":
        if not text:
            send_message(chat_id, "Пожалуйста, напишите ваше имя.")
            return
        data["name"] = text

        if data["role"] == "ВОДИТЕЛЬ":
            STATE[chat_id]["step"] = "car"
            send_message(
                chat_id,
                "Напишите марку и цвет авто (например: VW Passat, белый).",
                reply_markup=REMOVE_KB
            )
        else:
            # пассажир — пропускаем авто и номер
            data["car"] = ""
            data["plate"] = ""
            STATE[chat_id]["step"] = "from"
            send_message(
                chat_id,
                "Откуда вы выезжаете? Напишите город или отправьте местоположение.",
                reply_markup=LOCATION_KB
            )

    # 3) АВТО (только водитель)
    elif step == "car":
        data["car"] = text if text else ""
        STATE[chat_id]["step"] = "plate_choice"
        send_message(
            chat_id,
            "Хотите указать номер авто?",
            reply_markup=PLATE_CHOICE_KB
        )

    # 4) ВЫБОР: НОМЕР АВТО
    elif step == "plate_choice":
        if text == "Добавить номер авто":
            STATE[chat_id]["step"] = "plate"
            send_message(chat_id, "Напишите номер машины полностью.", reply_markup=REMOVE_KB)
        elif text == "Без номера":
            data["plate"] = ""
            STATE[chat_id]["step"] = "from"
            send_message(
                chat_id,
                "Откуда вы выезжаете? Напишите город или отправьте местоположение.",
                reply_markup=LOCATION_KB
            )
        else:
            send_message(chat_id, "Пожалуйста, выберите кнопку.", reply_markup=PLATE_CHOICE_KB)

    # 5) НОМЕР АВТО
    elif step == "plate":
        data["plate"] = text
        STATE[chat_id]["step"] = "from"
        send_message(
            chat_id,
            "Откуда вы выезжаете? Напишите город или отправьте местоположение.",
            reply_markup=LOCATION_KB
        )

    # 6) ОТКУДА
    elif step == "from":
        if location_str:
            data["from"] = f"локация: {location_str}"
        elif text:
            data["from"] = text
        else:
            send_message(chat_id, "Отправьте город или местоположение.", reply_markup=LOCATION_KB)
            return

        STATE[chat_id]["step"] = "to"
        send_message(
            chat_id,
            "Куда вы едете? Напишите город или отправьте местоположение.",
            reply_markup=LOCATION_KB
        )

    # 7) КУДА
    elif step == "to":
        if location_str:
            data["to"] = f"локация: {location_str}"
        elif text:
            data["to"] = text
        else:
            send_message(chat_id, "Отправьте город или местоположение.", reply_markup=LOCATION_KB)
            return

        STATE[chat_id]["step"] = "date"
        send_message(
            chat_id,
            "Когда вы планируете поездку?",
            reply_markup=DATE_KEYBOARD
        )

    # 8) ДАТА (кнопки)
    elif step == "date":
        if text == "Сегодня":
            data["date"] = "Сегодня"
            STATE[chat_id]["step"] = "time"
            send_message(chat_id, "Во сколько выезжаете? Напишите время, например 18:30.", reply_markup=REMOVE_KB)
        elif text == "Завтра":
            data["date"] = "Завтра"
            STATE[chat_id]["step"] = "time"
            send_message(chat_id, "Во сколько выезжаете? Напишите время, например 09:00.", reply_markup=REMOVE_KB)
        elif text == "Другая дата":
            STATE[chat_id]["step"] = "date_custom"
            send_message(chat_id, "Напишите дату, например 05.01 или 5 января.", reply_markup=REMOVE_KB)
        else:
            send_message(chat_id, "Выберите: Сегодня, Завтра или Другая дата.", reply_markup=DATE_KEYBOARD)

    # 9) ДАТА (своя)
    elif step == "date_custom":
        if not text:
            send_message(chat_id, "Напишите дату текстом, например 10 января.")
            return
        data["date"] = text
        STATE[chat_id]["step"] = "time"
        send_message(chat_id, "Во сколько выезжаете? Напишите время, например 18:30.")

    # 10) ВРЕМЯ
    elif step == "time":
        if not text:
            send_message(chat_id, "Напишите время, например 18:30.")
            return
        data["time"] = text
        STATE[chat_id]["step"] = "comment_choice"
        send_message(
            chat_id,
            "Хотите добавить комментарий (багаж, дети, условия и т.п.)?",
            reply_markup=COMMENT_CHOICE_KB
        )

    # 11) ВЫБОР КОММЕНТАРИЯ
    elif step == "comment_choice":
        if text == "Добавить комментарий":
            STATE[chat_id]["step"] = "comment"
            send_message(chat_id, "Напишите ваш комментарий.", reply_markup=REMOVE_KB)
        elif text == "Без комментария":
            data["comment"] = ""
            STATE[chat_id]["step"] = "price_mode"
            send_message(chat_id, "Как укажем цену?", reply_markup=PRICE_MODE_KB)
        else:
            send_message(chat_id, "Пожалуйста, выберите кнопку.", reply_markup=COMMENT_CHOICE_KB)

    # 12) КОММЕНТАРИЙ
    elif step == "comment":
        data["comment"] = text
        STATE[chat_id]["step"] = "price_mode"
        send_message(chat_id, "Как укажем цену?", reply_markup=PRICE_MODE_KB)

    # 13) ВЫБОР ЦЕНЫ
    elif step == "price_mode":
        if text == "Цена обсуждается":
            data["price"] = "Цена обсуждается"
            STATE[chat_id]["step"] = "contact"
            send_message(chat_id, "Напишите номер телефона или Telegram для связи.", reply_markup=REMOVE_KB)
        elif text == "Указать цену":
            STATE[chat_id]["step"] = "price_value"
            send_message(chat_id, "Напишите цену за место, например 120 MDL.", reply_markup=REMOVE_KB)
        else:
            send_message(chat_id, "Выберите вариант: Указать цену или Цена обсуждается.", reply_markup=PRICE_MODE_KB)

    # 14) КОНКРЕТНАЯ ЦЕНА
    elif step == "price_value":
        if not text:
            send_message(chat_id, "Напишите цену, например 150 MDL.")
            return
        data["price"] = text
        STATE[chat_id]["step"] = "contact"
        send_message(chat_id, "Напишите номер телефона или Telegram для связи.")

    # 15) КОНТАКТЫ
    elif step == "contact":
        if not text:
            send_message(chat_id, "Нужно указать хотя бы один способ связи.")
            return
        data["contact"] = text

        # формируем объявление
        comment_part = f"\n💬 *Комментарий:* {data['comment']}" if data.get("comment") else ""

        car_block = ""
        if data["role"] == "ВОДИТЕЛЬ":
            if data.get("car"):
                car_block += f"\n🚘 *Авто:* {data['car']}"
            if data.get("plate"):
                car_block += f"\n🔢 *Номер авто:* {data['plate']}"

        text_out = (
            "🚗 *ПОПУТЧИКИ — ПОЕЗДКА*\n"
            "———————————————\n"
            f"👤 *Имя:* {data['name']}\n"
            f"👤 *Роль:* {data['role']}\n"
            f"📍 *Откуда:* {data['from']}\n"
            f"📍 *Куда:* {data['to']}\n"
            f"📅 *Дата:* {data['date']}\n"
            f"⏰ *Время:* {data['time']}\n"
            f"💲 *Цена:* {data['price']}"
            f"{car_block}"
            f"\n📞 *Контакты:* {data['contact']}"
            f"{comment_part}"
            f"\n\n🤖 *Бот:* {BOT_USERNAME}"
        )

        # блок про безопасность
        if SAFETY_URL and "http" in SAFETY_URL:
            text_out += f"\n⚠ *Безопасность:* прочитайте памятку: {SAFETY_URL}"
        else:
            text_out += "\n⚠ *Безопасность:* внимательно проверяйте людей и не отправляйте предоплату незнакомым."

        send_to_channel(text_out)
        send_message(chat_id, "Ваше объявление опубликовано в канале. Спасибо!", reply_markup=REMOVE_KB)

        del STATE[chat_id]


def main():
    offset = None
    while True:
        params = {"timeout": 50}
        if offset is not None:
            params["offset"] = offset

        resp = requests.get(f"{BASE_URL}/getUpdates", params=params)
        data = resp.json()

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            handle_text(update)

        time.sleep(1)


if __name__ == "__main__":
    main()

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    # здесь запускается твой бот
    main()

