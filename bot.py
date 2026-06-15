# bot.py
import os
import json
import random
import logging
import time
from threading import Thread
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")

URL = f"https://api.telegram.org/bot{TOKEN}"

QUESTIONS = [
    {"nick": "Galo", "correct": "Atlético Mineiro", "wrong": ["Cruzeiro", "América-MG", "Grêmio"]},
    {"nick": "Falcão do Pici", "correct": "Fortaleza", "wrong": ["Ceará", "Ferroviário", "Sport"]},
    {"nick": "Peixe", "correct": "Santos", "wrong": ["São Paulo", "Palmeiras", "Corinthians"]},
    {"nick": "Mengão", "correct": "Flamengo", "wrong": ["Fluminense", "Vasco", "Botafogo"]},
    {"nick": "Coringão", "correct": "Corinthians", "wrong": ["Palmeiras", "São Paulo", "Santos"]},
    {"nick": "Leão", "correct": "Sport", "wrong": ["Náutico", "Santa Cruz", "Bahia"]},
    {"nick": "Verdão", "correct": "Palmeiras", "wrong": ["Grêmio", "Internacional", "São Paulo"]},
    {"nick": "Tricolor Paulista", "correct": "São Paulo", "wrong": ["Fluminense", "Grêmio", "Bahia"]},
    {"nick": "Furacão", "correct": "Athletico Paranaense", "wrong": ["Coritiba", "Paraná", "Internacional"]},
    {"nick": "Raposa", "correct": "Cruzeiro", "wrong": ["Atlético-MG", "América-MG", "Grêmio"]},
]

user_scores = {}
user_state = {}
user_current_q = {}
user_options = {}

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{URL}/sendMessage", json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_question(chat_id):
    q = random.choice(QUESTIONS)
    user_current_q[chat_id] = q
    
    options = [q["correct"]] + q["wrong"]
    random.shuffle(options)
    user_options[chat_id] = options
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"A) {options[0]}", "callback_data": "0"}],
            [{"text": f"B) {options[1]}", "callback_data": "1"}],
            [{"text": f"C) {options[2]}", "callback_data": "2"}],
            [{"text": f"D) {options[3]}", "callback_data": "3"}],
        ]
    }
    
    send_message(chat_id, f"⚽ Which club is called *{q['nick']}*?", keyboard)

def handle_start(chat_id):
    user_scores[chat_id] = 0
    user_state[chat_id] = "awaiting_sim"
    send_message(chat_id, 
        "⚽ *LUDOVIC APOSTAS AO VIVO* ⚽\n\n"
        "Responda qual time corresponde ao apelido.\n"
        "Cada acerto = 1 ponto.\n\n"
        "Digite *Sim* para jogar ou *Não* para sair.")

def handle_text(chat_id, text):
    state = user_state.get(chat_id, "idle")
    text_lower = text.strip().lower()
    
    if state == "awaiting_sim":
        if text_lower == "sim":
            user_state[chat_id] = "answering"
            send_question(chat_id)
        elif text_lower == "não":
            send_message(chat_id, "Ok! /start quando quiser jogar.")
            user_state[chat_id] = "idle"
        else:
            send_message(chat_id, 'Responda apenas "Sim" ou "Não".')
    else:
        send_message(chat_id, 'Use /start para começar ou /cancel para sair.')

def handle_callback(chat_id, callback_data, message_id):
    if user_state.get(chat_id) != "answering":
        return
    
    idx = int(callback_data)
    q = user_current_q.get(chat_id)
    options = user_options.get(chat_id)
    
    if not q or not options:
        send_message(chat_id, "Erro. Use /start")
        return
    
    selected = options[idx]
    correct = (selected == q["correct"])
    
    if correct:
        user_scores[chat_id] = user_scores.get(chat_id, 0) + 1
        msg = f"✅ Correto! {q['nick']} é {q['correct']}.\n🏆 Pontos: {user_scores[chat_id]}"
    else:
        msg = f"❌ Errado! {q['nick']} é {q['correct']}, não {selected}.\n📊 Pontos: {user_scores.get(chat_id, 0)}"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Sim", "callback_data": "again_yes"}],
            [{"text": "❌ Não", "callback_data": "again_no"}]
        ]
    }
    
    # Edit the original message
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": f"{msg}\n\nJogar novamente?",
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    requests.post(f"{URL}/editMessageText", json=payload, timeout=5)
    user_state[chat_id] = "awaiting_again"

def handle_again(chat_id, callback_data, message_id):
    if callback_data == "again_yes":
        user_state[chat_id] = "answering"
        send_question(chat_id)
        # Delete the old message with the buttons
        requests.post(f"{URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id}, timeout=5)
    else:
        score = user_scores.get(chat_id, 0)
        send_message(chat_id, f"🏁 Fim! Pontuação final: {score}\n/start para novo jogo.")
        user_state[chat_id] = "idle"
        requests.post(f"{URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id}, timeout=5)

def handle_cancel(chat_id):
    send_message(chat_id, "Cancelado. /start para jogar.")
    user_state[chat_id] = "idle"

def poll():
    offset = 0
    while True:
        try:
            response = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code != 200:
                time.sleep(1)
                continue
                
            data = response.json()
            if not data.get("ok"):
                time.sleep(1)
                continue
                
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    if "text" in update["message"]:
                        text = update["message"]["text"]
                        if text == "/start":
                            handle_start(chat_id)
                        elif text == "/cancel":
                            handle_cancel(chat_id)
                        else:
                            handle_text(chat_id, text)
                
                elif "callback_query" in update:
                    chat_id = update["callback_query"]["from"]["id"]
                    callback_data = update["callback_query"]["data"]
                    message_id = update["callback_query"]["message"]["message_id"]
                    
                    if callback_data in ["0", "1", "2", "3"]:
                        handle_callback(chat_id, callback_data, message_id)
                    elif callback_data in ["again_yes", "again_no"]:
                        handle_again(chat_id, callback_data, message_id)
                    
                    # Answer callback query
                    requests.post(f"{URL}/answerCallbackQuery", json={"callback_query_id": update["callback_query"]["id"]}, timeout=5)
                    
        except Exception as e:
            logger.error(f"Poll error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    logger.info("Bot started with requests method")
    poll()
