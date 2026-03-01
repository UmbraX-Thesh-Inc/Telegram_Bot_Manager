import os
import io
import zipfile
import requests
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import upload_file_to_repo, list_repositories
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import UPLOAD_REPO, UPLOAD_FILE
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'upload_repo':
        await query.answer()
        repos, _ = list_repositories()
        keyboard = []
        for r in repos:
            keyboard.append([InlineKeyboardButton(
                f"📁 {r['name']}",
                callback_data=f'uploadto_{r["name"]}'
            )])
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "📤 *Subir Archivos a GitHub*\n\n"
            "Selecciona el repositorio destino:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return UPLOAD_REPO

    if query and query.data.startswith('uploadto_'):
        await query.answer()
        repo_name = query.data.replace('uploadto_', '')
        context.user_data['upload_repo'] = repo_name
        context.user_data['upload_path'] = ''
        await query.edit_message_text(
            f"📤 Subiendo a: `{repo_name}`\n\n"
            "Envía el archivo que deseas subir.\n"
            "_(También puedes enviar un ZIP y se extraerá)_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return UPLOAD_FILE

    # Text input for path
    msg = update.message
    if msg and msg.text:
        context.user_data['upload_path'] = msg.text.strip().strip('/')
        await msg.reply_text(
            f"📂 Carpeta destino: `{context.user_data['upload_path']}`\n"
            "Ahora envía el archivo:",
            parse_mode='Markdown'
        )
        return UPLOAD_FILE


async def upload_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    repo = context.user_data.get('upload_repo', '')
    path_prefix = context.user_data.get('upload_path', '')

    if not repo:
        await msg.reply_text("❌ Error: no se seleccionó repositorio.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if not msg.document:
        await msg.reply_text("❌ Por favor envía un archivo válido.")
        return UPLOAD_FILE

    doc = msg.document
    file_name = doc.file_name
    file_path = f"{path_prefix}/{file_name}" if path_prefix else file_name

    await msg.reply_text(f"⏳ Subiendo `{file_name}`...")

    tg_file = await context.bot.get_file(doc.file_id)
    content = bytes(await tg_file.download_as_bytearray())

    # Si es ZIP, extraer y subir
    if file_name.endswith('.zip'):
        await msg.reply_text("📦 ZIP detectado, extrayendo archivos...")
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            uploaded = 0
            errors = 0
            for zf in z.namelist():
                if zf.endswith('/'):
                    continue
                zpath = f"{path_prefix}/{zf}" if path_prefix else zf
                file_content = z.read(zf)
                _, status = upload_file_to_repo(repo, zpath, file_content, f'Upload {zf} via bot')
                if status in (200, 201):
                    uploaded += 1
                else:
                    errors += 1
            await msg.reply_text(
                f"✅ ZIP extraído y subido\n"
                f"📁 Archivos subidos: `{uploaded}`\n"
                f"❌ Errores: `{errors}`",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            await msg.reply_text(f"❌ Error procesando ZIP: `{e}`", parse_mode='Markdown', reply_markup=main_menu_keyboard())
    else:
        result, status = upload_file_to_repo(repo, file_path, content)
        if status in (200, 201):
            url = result.get('content', {}).get('html_url', '')
            await msg.reply_text(
                f"✅ *Archivo subido exitosamente*\n\n"
                f"📄 `{file_path}`\n"
                f"🔗 [Ver en GitHub]({url})",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            err = result.get('message', 'Error')
            await msg.reply_text(
                f"❌ Error al subir:\n`{err}`",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )

    context.user_data.clear()
    return ConversationHandler.END
