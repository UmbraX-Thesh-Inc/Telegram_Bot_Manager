import io
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import download_repo_zip, get_repo_contents, get_file_content, get_repo_info, list_repositories
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import ZIP_REPO
import asyncio

# Handler principal para descargar ZIP
async def download_zip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'download_zip':
        await query.answer()
        repos, _ = list_repositories()
        keyboard = []
        for r in repos:
            owner = r['owner']['login']
            keyboard.append([InlineKeyboardButton(
                f"📁 {r['name']}",
                callback_data=f'zipdl_{owner}_{r["name"]}'
            )])
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "📥 *Descargar Repositorio ZIP*\n\nSelecciona el repositorio:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ZIP_REPO

    if query and (query.data.startswith('zipdl_') or query.data.startswith('zip_')):
        await query.answer()
        parts = query.data.split('_', 1)[1].rsplit('_', 1)
        owner = parts[0] if len(parts) > 1 else ''
        repo = parts[1] if len(parts) > 1 else parts[0]
        await _send_zip_with_dynamic_progress(query, context, owner, repo)
        return ConversationHandler.END

    msg = update.message
    if msg:
        text = msg.text.strip()
        if '/' in text:
            owner, repo = text.split('/', 1)
        else:
            from config.settings import GITHUB_USERNAME
            owner, repo = GITHUB_USERNAME, text
        await msg.reply_text(f"⏳ Preparando ZIP de `{owner}/{repo}`...")
        await _send_zip_msg_with_dynamic_progress(msg, context, owner, repo)
        return ConversationHandler.END

# Barra de progreso en un solo mensaje
async def _send_zip_with_dynamic_progress(query, context, owner: str, repo: str):
    info, status_info = get_repo_info(owner, repo)
    if status_info != 200:
        await query.edit_message_text("❌ No se pudo obtener información del repositorio.", reply_markup=main_menu_keyboard())
        return

    desc = info.get('description', 'Sin descripción')
    stars = info.get('stargazers_count', 0)
    forks = info.get('forks_count', 0)
    size_kb = info.get('size', 0)

    msg_text = (
        f"📥 Preparando ZIP de *{owner}/{repo}*\n"
        f"📝 Descripción: {desc}\n"
        f"⭐ Stars: {stars} | 🍴 Forks: {forks} | 📦 Tamaño aprox: {size_kb} KB\n\n"
        f"⏳ Descargando..."
    )
    await query.edit_message_text(msg_text, parse_mode='Markdown')

    # Descargar ZIP
    content, status = download_repo_zip(owner, repo)
    if status not in (200, 302) or not content:
        await query.edit_message_text(f"❌ Error descargando ZIP. Código: `{status}`", reply_markup=main_menu_keyboard())
        return

    zip_file = io.BytesIO(content)
    zip_file.name = f"{repo}.zip"

    # Crear mensaje de progreso
    progress_msg = await query.edit_message_text("📦 Enviando ZIP: [                    ] 0%", parse_mode='Markdown')

    # Simular barra de progreso en un solo mensaje
    total_steps = 10
    for i in range(1, total_steps + 1):
        bar = '█' * i + '-' * (total_steps - i)
        percent = int(i / total_steps * 100)
        await progress_msg.edit_text(f"📦 Enviando ZIP: [{bar}] {percent}%", parse_mode='Markdown')
        await asyncio.sleep(0.2)  # Simula tiempo de envío

    # Enviar ZIP final
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=zip_file,
        filename=f"{repo}.zip",
        caption=f"✅ ZIP de *{owner}/{repo}* enviado con éxito",
        parse_mode='Markdown'
    )

    await query.edit_message_text(f"✅ ZIP de *{owner}/{repo}* enviado", parse_mode='Markdown', reply_markup=main_menu_keyboard())

# Mismo concepto para input por mensaje
async def _send_zip_msg_with_dynamic_progress(msg, context, owner: str, repo: str):
    info, status_info = get_repo_info(owner, repo)
    if status_info != 200:
        await msg.reply_text("❌ No se pudo obtener información del repositorio.", reply_markup=main_menu_keyboard())
        return

    desc = info.get('description', 'Sin descripción')
    stars = info.get('stargazers_count', 0)
    forks = info.get('forks_count', 0)
    size_kb = info.get('size', 0)

    await msg.reply_text(
        f"📥 Preparando ZIP de *{owner}/{repo}*\n"
        f"📝 Descripción: {desc}\n"
        f"⭐ Stars: {stars} | 🍴 Forks: {forks} | 📦 Tamaño aprox: {size_kb} KB\n\n"
        f"⏳ Descargando...",
        parse_mode='Markdown'
    )

    content, status = download_repo_zip(owner, repo)
    if status not in (200, 302) or not content:
        await msg.reply_text(f"❌ Error descargando ZIP. Código: `{status}`", reply_markup=main_menu_keyboard())
        return

    zip_file = io.BytesIO(content)
    zip_file.name = f"{repo}.zip"

    progress_msg = await msg.reply_text("📦 Enviando ZIP: [                    ] 0%", parse_mode='Markdown')

    total_steps = 10
    for i in range(1, total_steps + 1):
        bar = '█' * i + '-' * (total_steps - i)
        percent = int(i / total_steps * 100)
        await progress_msg.edit_text(f"📦 Enviando ZIP: [{bar}] {percent}%", parse_mode='Markdown')
        await asyncio.sleep(0.2)

    await msg.reply_document(
        document=zip_file,
        filename=f"{repo}.zip",
        caption=f"✅ ZIP de *{owner}/{repo}* enviado con éxito",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )