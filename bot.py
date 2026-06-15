# bot.py
import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTING, PLAY_AGAIN = range(2)

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
    {"nick": "Gigante da Colina", "correct": "Vasco", "wrong": ["Flamengo", "Fluminense", "Botafogo"]},
]

user_scores = {}

def format_question(q):
    return f"⚽ Which club is called *{q['nick']}*?"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_scores[user_id] = 0
    
    await update.message.reply_text(
        "⚽ *LUDOVIC APOSTAS AO VIVO* ⚽\n\n"
        "Responda qual time corresponde ao apelido.\n"
        "Cada acerto = 1 ponto.\n\n"
        "Digite *Sim* para jogar ou *Não* para sair.",
        parse_mode="Markdown"
    )
    return SELECTING

async def handle_start_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    
    if text == "sim":
        return await ask_question(update, context)
    elif text == "não":
        await update.message.reply_text("Ok! /start quando quiser jogar.")
        return ConversationHandler.END
    else:
        await update.message.reply_text('Responda apenas "Sim" ou "Não".')
        return SELECTING

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = random.choice(QUESTIONS)
    context.user_data["current_q"] = q
    
    options = [q["correct"]] + q["wrong"]
    random.shuffle(options)
    context.user_data["options"] = options
    
    keyboard = [
        [InlineKeyboardButton(f"A) {options[0]}", callback_data="0")],
        [InlineKeyboardButton(f"B) {options[1]}", callback_data="1")],
        [InlineKeyboardButton(f"C) {options[2]}", callback_data="2")],
        [InlineKeyboardButton(f"D) {options[3]}", callback_data="3")],
    ]
    
    await update.message.reply_text(
        format_question(q),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING

async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    idx = int(query.data)
    
    q = context.user_data.get("current_q")
    options = context.user_data.get("options")
    
    if not q or not options:
        await query.edit_message_text("Erro. Use /start")
        return ConversationHandler.END
    
    selected = options[idx]
    correct = (selected == q["correct"])
    
    if correct:
        user_scores[user_id] += 1
        msg = f"✅ Correto! {q['nick']} é {q['correct']}.\n🏆 Pontos: {user_scores[user_id]}"
    else:
        msg = f"❌ Errado! {q['nick']} é {q['correct']}, não {selected}.\n📊 Pontos: {user_scores[user_id]}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sim", callback_data="again_yes")],
        [InlineKeyboardButton("Não", callback_data="again_no")]
    ])
    
    await query.edit_message_text(f"{msg}\n\nJogar novamente?", reply_markup=keyboard)
    return PLAY_AGAIN

async def play_again_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "again_yes":
        q = random.choice(QUESTIONS)
        context.user_data["current_q"] = q
        
        options = [q["correct"]] + q["wrong"]
        random.shuffle(options)
        context.user_data["options"] = options
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"A) {options[0]}", callback_data="0")],
            [InlineKeyboardButton(f"B) {options[1]}", callback_data="1")],
            [InlineKeyboardButton(f"C) {options[2]}", callback_data="2")],
            [InlineKeyboardButton(f"D) {options[3]}", callback_data="3")],
        ])
        
        await query.edit_message_text(format_question(q), parse_mode="Markdown", reply_markup=keyboard)
        return SELECTING
    else:
        score = user_scores.get(user_id, 0)
        await query.edit_message_text(f"🏁 Fim! Pontuação final: {score}\n/start para novo jogo.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado. /start para jogar.")
    return ConversationHandler.END

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")
    
    # Fixed: Use Application.builder() correctly
    application = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_choice),
                CallbackQueryHandler(answer_callback)
            ],
            PLAY_AGAIN: [CallbackQueryHandler(play_again_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
