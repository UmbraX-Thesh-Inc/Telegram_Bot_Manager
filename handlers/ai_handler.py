from google import genai
from google.genai import types
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import GEMINI_API_KEY
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import AI_MESSAGE
import logging

logger = logging.getLogger(__name__)

# Cliente nuevo SDK (usa HTTP REST puro, sin grpcio ni protobuf)
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = (
    "Eres un asistente de IA integrado en un bot de Telegram para gestionar GitHub. "
    "Eres experto en programación, Git, GitHub, y puedes ayudar a los usuarios con código, "
    "resolución de problemas, revisión de código, arquitectura de software y más. "
    "Responde en español, de forma clara y concisa. "
    "Cuando muestres código, usa bloques de código con el lenguaje apropiado."
)

# Historial por usuario: {user_id: [{"role": "user/model", "parts": "texto"}]}
chat_histories: dict = {}


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'ai_chat':
        await query.answer()
        user_id = query.from_user.id
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
            "_Escribe_ `salir` _para volver al menú_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return AI_MESSAGE

    msg = update.message
    if not msg:
        return AI_MESSAGE

    user_id = msg.from_user.id
    user_text = msg.text.strip()

    if user_text.lower() in ('/exit', 'salir', 'exit', 'menu', '/menu'):
        await msg.reply_text("👋 Chat de IA cerrado.", reply_markup=main_menu_keyboard())
        chat_histories.pop(user_id, None)
        return ConversationHandler.END

    thinking_msg = await msg.reply_text("🤔 Pensando...")

    try:
        history = chat_histories.get(user_id, [])

        # Construir contenidos con historial
        contents = []
        for h in history:
            contents.append(
                types.Content(role=h["role"], parts=[types.Part(text=h["parts"])])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        answer = response.text

        # Actualizar historial
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].append({"role": "user", "parts": user_text})
        chat_histories[user_id].append({"role": "model", "parts": answer})

        # Limitar historial a últimos 20 mensajes
        if len(chat_histories[user_id]) > 20:
            chat_histories[user_id] = chat_histories[user_id][-20:]

        await thinking_msg.delete()

        # Dividir respuestas largas
        if len(answer) > 4000:
            chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for i, chunk in enumerate(chunks):
                label = f"\n_Parte {i+1}/{len(chunks)}_" if len(chunks) > 1 else ''
                await msg.reply_text(chunk + label, parse_mode='Markdown')
        else:
            await msg.reply_text(answer, parse_mode='Markdown')

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu'),
            InlineKeyboardButton("🗑️ Limpiar Chat", callback_data='ai_chat')
        ]])
        await msg.reply_text("_¿Algo más?_", parse_mode='Markdown', reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await msg.reply_text(
            f"❌ *Error con Gemini AI:*\n`{str(e)}`\n\nIntenta de nuevo.",
            parse_mode='Markdown'
        )

    return AI_MESSAGE
