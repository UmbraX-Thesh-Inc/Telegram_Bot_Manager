import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import GEMINI_API_KEY
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import AI_MESSAGE

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Historial de chat por usuario
chat_sessions = {}

SYSTEM_PROMPT = (
    "Eres un asistente de IA integrado en un bot de Telegram para gestionar GitHub. "
    "Eres experto en programación, Git, GitHub, y puedes ayudar a los usuarios con código, "
    "resolución de problemas, revisión de código, arquitectura de software y más. "
    "Responde en español, de forma clara y concisa."
)


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'ai_chat':
        await query.answer()
        user_id = query.from_user.id
        # Reset chat session
        chat_sessions[user_id] = model.start_chat(history=[])
        await query.edit_message_text(
            "🤖 *IA Gemini — Chat Activado*\n\n"
            "Puedo ayudarte con:\n"
            "• 💻 Código y programación\n"
            "• 🐙 Git y GitHub\n"
            "• 🏗️ Arquitectura de software\n"
            "• 🔍 Revisión de código\n"
            "• ❓ Cualquier pregunta técnica\n\n"
            "Escribe tu mensaje:",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return AI_MESSAGE

    msg = update.message
    if not msg:
        return AI_MESSAGE

    user_id = msg.from_user.id
    user_text = msg.text.strip()

    # Comandos especiales
    if user_text.lower() in ('/exit', 'salir', 'exit', 'menu'):
        await msg.reply_text(
            "👋 Chat de IA cerrado. ¡Hasta luego!",
            reply_markup=main_menu_keyboard()
        )
        chat_sessions.pop(user_id, None)
        return ConversationHandler.END

    await msg.reply_text("🤔 Procesando...")

    try:
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])

        chat = chat_sessions[user_id]
        full_prompt = f"{SYSTEM_PROMPT}\n\nUsuario: {user_text}" if len(chat.history) == 0 else user_text
        response = chat.send_message(full_prompt)
        answer = response.text

        # Split long responses
        if len(answer) > 4000:
            parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for i, part in enumerate(parts):
                suffix = f"\n\n_[{i+1}/{len(parts)}]_" if len(parts) > 1 else ''
                await msg.reply_text(part + suffix, parse_mode='Markdown')
        else:
            await msg.reply_text(answer, parse_mode='Markdown')

        # Show continue options
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu'),
             InlineKeyboardButton("🔄 Nueva Pregunta", callback_data='ai_chat')]
        ])
        await msg.reply_text("¿Qué más necesitas?", reply_markup=keyboard)

    except Exception as e:
        await msg.reply_text(
            f"❌ Error con Gemini AI:\n`{str(e)}`\n\nIntenta de nuevo.",
            parse_mode='Markdown'
        )

    return AI_MESSAGE
