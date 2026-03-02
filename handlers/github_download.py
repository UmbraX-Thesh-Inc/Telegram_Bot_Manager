import io
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import download_repo_zip, get_repo_contents, get_file_content, list_repositories
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import ZIP_REPO
import base64


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
            "📥 *Descargar Repositorio ZIP*\n\n"
            "Selecciona el repositorio:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ZIP_REPO

    # Handle zipdl_ callbacks from repos list
    if query and query.data.startswith('zipdl_') or query and query.data.startswith('zip_'):
        await query.answer()
        parts = query.data.split('_', 1)[1].rsplit('_', 1)
        owner = parts[0] if len(parts) > 1 else ''
        repo = parts[1] if len(parts) > 1 else parts[0]
        await _send_zip(query, context, owner, repo)
        return ConversationHandler.END

    # Text input (owner/repo)
    msg = update.message
    if msg:
        text = msg.text.strip()
        if '/' in text:
            owner, repo = text.split('/', 1)
        else:
            from config.settings import GITHUB_USERNAME
            owner, repo = GITHUB_USERNAME, text
        await msg.reply_text(f"⏳ Preparando ZIP de `{owner}/{repo}`...")
        await _send_zip_msg(msg, context, owner, repo)
        return ConversationHandler.END


async def _send_zip(query, context, owner: str, repo: str):
    await query.edit_message_text(f"⏳ Descargando ZIP de `{owner}/{repo}`...", parse_mode='Markdown')
    content, status = download_repo_zip(owner, repo)
    if status in (200, 302) and content:
        zip_file = io.BytesIO(content)
        zip_file.name = f"{repo}.zip"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=zip_file,
            filename=f"{repo}.zip",
            caption=f"📦 *{owner}/{repo}*\n✅ ZIP descargado exitosamente",
            parse_mode='Markdown'
        )
        await query.edit_message_text(
            f"✅ ZIP de `{owner}/{repo}` enviado",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            f"❌ Error descargando ZIP. Código: `{status}`",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )


async def _send_zip_msg(msg, context, owner: str, repo: str):
    content, status = download_repo_zip(owner, repo)
    if status in (200, 302) and content:
        zip_file = io.BytesIO(content)
        zip_file.name = f"{repo}.zip"
        await msg.reply_document(
            document=zip_file,
            filename=f"{repo}.zip",
            caption=f"📦 *{owner}/{repo}*\n✅ ZIP descargado exitosamente",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    else:
        await msg.reply_text(
            f"❌ Error descargando ZIP. Código: `{status}`",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )


async def download_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, owner: str, repo: str, path: str):
    query = update.callback_query
    if query:
        await query.answer()

    result, status = get_file_content(owner, repo, path)
    if status != 200:
        if query:
            await query.edit_message_text("❌ No se pudo obtener el archivo.", reply_markup=main_menu_keyboard())
        return

    content_b64 = result.get('content', '')
    content = base64.b64decode(content_b64)
    filename = path.split('/')[-1]

    file_io = io.BytesIO(content)
    file_io.name = filename

    chat_id = query.message.chat_id if query else update.message.chat_id
    await context.bot.send_document(
        chat_id=chat_id,
        document=file_io,
        filename=filename,
        caption=f"📄 `{owner}/{repo}/{path}`",
        parse_mode='Markdown'
    )


async def list_files_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, owner: str, repo: str, path: str = ''):
    query = update.callback_query
    if query:
        await query.answer()

    contents, status = get_repo_contents(owner, repo, path)
    if status != 200:
        await query.edit_message_text("❌ Error obteniendo contenido.", reply_markup=main_menu_keyboard())
        return

    keyboard = []
    if path:
        parent = '/'.join(path.split('/')[:-1])
        keyboard.append([InlineKeyboardButton("📂 ..", callback_data=f'files_{owner}_{repo}_{parent}')])

    for item in contents[:20]:
        name = item['name']
        itype = item['type']
        icon = '📁' if itype == 'dir' else '📄'
        item_path = item['path']
        if itype == 'dir':
            keyboard.append([InlineKeyboardButton(
                f"{icon} {name}/",
                callback_data=f'files_{owner}_{repo}_{item_path}'
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {name}",
                callback_data=f'dlfile_{owner}_{repo}_{item_path}'
            )])

    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu')])
    current_path = path if path else '/'
    await query.edit_message_text(
        f"📂 *{owner}/{repo}*\n📍 `{current_path}`",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
