import io
import asyncio
import time
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import download_repo_zip_stream, get_repo_info, list_repositories
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import ZIP_REPO

CHUNK_SIZE = 256 * 1024  # 256 KB
BAR_LENGTH = 20  # longitud barra de progreso

async def download_zip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'download_zip':
        await query.answer()
        repos, _ = list_repositories()
        keyboard = [
            [InlineKeyboardButton(f"📁 {r['name']}", callback_data=f'zipdl_{r["owner"]["login"]}_{r["name"]}')]
            for r in repos
        ]
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "📥 *Descargar Repositorio ZIP*\nSelecciona el repositorio:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ZIP_REPO

    if query and query.data.startswith('zipdl_'):
        await query.answer()
        parts = query.data.split('_', 2)
        owner, repo = parts[1], parts[2]
        await _send_zip_stream(query, context, owner, repo)
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
        query_fake = type('obj', (), {'callback_query': None, 'message': msg})
        await _send_zip_stream(query_fake, context, owner, repo)
        return ConversationHandler.END


async def _send_zip_stream(query, context, owner: str, repo: str):
    repo_info, status_info = get_repo_info(owner, repo)
    if status_info != 200 or not repo_info:
        await query.message.reply_text("❌ No se pudo obtener info del repositorio.", reply_markup=main_menu_keyboard())
        return

    # Datos del repo
    desc = repo_info.get('description') or "Sin descripción"
    private = "Privado 🔒" if repo_info.get('private') else "Público 🌐"
    stars = repo_info.get('stargazers_count', 0)
    forks = repo_info.get('forks_count', 0)
    updated = repo_info.get('updated_at', 'Desconocido')

    info_text = (
        f"📦 *{owner}/{repo}*\n"
        f"📝 Descripción: {desc}\n"
        f"🔒 Privacidad: {private}\n"
        f"⭐ Stars: {stars} | 🍴 Forks: {forks}\n"
        f"🕒 Última actualización: {updated}\n\n"
        f"⏳ Descargando y subiendo ZIP..."
    )
    await query.message.reply_text(info_text, parse_mode='Markdown')

    # Stream del ZIP
    stream = download_repo_zip_stream(owner, repo)
    if not stream:
        await query.message.reply_text("❌ Error descargando ZIP.", reply_markup=main_menu_keyboard())
        return

    chat_id = query.message.chat_id
    zip_file = io.BytesIO()
    total_bytes = 0
    start_time = time.time()
    progress_msg = await context.bot.send_message(
        chat_id,
        "📦 Subiendo ZIP...\n0% [░░░░░░░░░░░░░░░░░░░░] 0 KB"
    )

    # Leer stream y subir en chunks a Telegram
    async for chunk in stream:
        zip_file.write(chunk)
        total_bytes += len(chunk)
        elapsed = time.time() - start_time
        speed = total_bytes / 1024 / elapsed if elapsed > 0 else 0
        percent = min(int((total_bytes / stream.total_size) * 100), 100)
        filled = int(BAR_LENGTH * percent / 100)
        bar = '█' * filled + '░' * (BAR_LENGTH - filled)
        eta = (stream.total_size - total_bytes) / (speed * 1024) if speed > 0 else 0

        await progress_msg.edit_text(
            f"📦 Subiendo `{repo}.zip`...\n"
            f"{percent}% [{bar}] {total_bytes // 1024}/{stream.total_size // 1024} KB\n"
            f"⚡ Vel: {speed:.1f} KB/s | ⏱ ETA: {int(eta)}s"
        )
        await asyncio.sleep(0.05)

    zip_file.seek(0)
    zip_file.name = f"{repo}.zip"

    await context.bot.send_document(
        chat_id=chat_id,
        document=zip_file,
        filename=f"{repo}.zip",
        caption=f"✅ ZIP de `{owner}/{repo}` enviado correctamente",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )
    await progress_msg.delete()