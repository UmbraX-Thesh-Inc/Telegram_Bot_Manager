import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import GEMINI_API_KEY
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import AI_MESSAGE
import logging

logger = logging.getLogger(__name__)

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048,
}

SYSTEM_PROMPT = (
    "Eres un asistente de IA integrado en un bot de Telegram para gestionar GitHub. "
    "Eres experto en programación, Git, GitHub, y puedes ayudar a los usuarios con código, "
    "resolución de problemas, revisión de código, arquitectura de software y más. "
    "Responde en español, de forma clara y concisa. "
    "Cuando muestres código, usa bloques de código con el lenguaje apropiado."
)

# Historial de chat por usuario: {user_id: [{"role": ..., "parts": [...]}]}
chat_histories = {}


def _get_model():
    return genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
        system_instruction=SYSTEM_PROMPT
    )


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'ai_chat':
        await query.answer()
        user_id = query.from_user.id
        # Resetear historial
        chat_histories[user_id] = []
        await query.edit_message_text(
            "🤖 *IA Gemini — Chat Activado*\n\n"
            "Puedo ayudarte con:\n"
            "• 💻 Código y programación\n"
            "• 🐙 Git y GitHub\n"
            "• 🏗️ Arquitectura de software\n"
            "• 🔍 Revisión de código\n"
            "• ❓ Cualquier pregunta técnica\n\n"
            "✏️ Escribe tu mensaje:\n"
            "_Escribe `salir` para volver al menú_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return AI_MESSAGE

    msg = update.message
    if not msg:
        return AI_MESSAGE

    user_id = msg.from_user.id
    user_text = msg.text.strip()

    # Salir del chat
    if user_text.lower() in ('/exit', 'salir', 'exit', 'menu', '/menu'):
        await msg.reply_text(
            "👋 Chat de IA cerrado.",
            reply_markup=main_menu_keyboard()
        )
        chat_histories.pop(user_id, None)
        return ConversationHandler.END

    thinking_msg = await msg.reply_text("🤔 Pensando...")

    try:
        model = _get_model()

        # Mantener historial de conversación
        history = chat_histories.get(user_id, [])
        chat = model.start_chat(history=history)
        response = chat.send_message(user_text)
        answer = response.text

        # Actualizar historial
        chat_histories[user_id] = chat.history

        # Borrar mensaje de "pensando"
        await thinking_msg.delete()

        # Dividir respuestas largas
        if len(answer) > 4000:
            chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for i, chunk in enumerate(chunks):
                label = f"\n_Parte {i+1}/{len(chunks)}_" if len(chunks) > 1 else ''
                await msg.reply_text(chunk + label, parse_mode='Markdown')
        else:
            await msg.reply_text(answer, parse_mode='Markdown')

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu'),
                InlineKeyboardButton("🗑️ Limpiar Chat", callback_data='ai_chat')
            ]
        ])
        await msg.reply_text("_¿Algo más?_", parse_mode='Markdown', reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        await thinking_msg.delete()
        await msg.reply_text(
            f"❌ *Error con Gemini AI:*\n`{str(e)}`\n\nIntenta de nuevo.",
            parse_mode='Markdown'
        )

    return AI_MESSAGE
