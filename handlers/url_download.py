import io
import os
import requests
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import URL_INPUT

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit


async def url_download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'url_download':
        await query.answer()
        await query.edit_message_text(
            "🌐 *Descargar por URL*\n\n"
            "Envía el link del archivo a descargar.\n\n"
            "Soporta:\n"
            "• Archivos directos (ZIP, PDF, etc)\n"
            "• Cualquier URL descargable\n\n"
            "📏 Máximo: 50MB",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return URL_INPUT

    msg = update.message
    if not msg:
        return URL_INPUT

    url = msg.text.strip()

    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme in ('http', 'https'):
            await msg.reply_text("❌ URL inválida. Debe comenzar con http:// o https://")
            return URL_INPUT
    except Exception:
        await msg.reply_text("❌ URL inválida.")
        return URL_INPUT

    await msg.reply_text(f"⏳ Descargando desde:\n`{url}`", parse_mode='Markdown')

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()

        # Get filename
        content_disp = response.headers.get('content-disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[-1].strip('"\'')
        else:
            filename = parsed.path.split('/')[-1] or 'downloaded_file'

        if not filename or filename == '':
            filename = 'downloaded_file'

        # Check size
        content_length = int(response.headers.get('content-length', 0))
        if content_length > MAX_FILE_SIZE:
            await msg.reply_text(
                f"❌ Archivo demasiado grande: `{content_length // 1024 // 1024}MB`\n"
                f"Máximo permitido: 50MB",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END

        content = b''
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            downloaded += len(chunk)
            if downloaded > MAX_FILE_SIZE:
                await msg.reply_text("❌ Archivo demasiado grande.", reply_markup=main_menu_keyboard())
                return ConversationHandler.END

        content_type = response.headers.get('content-type', 'application/octet-stream')
        file_size = len(content)
        size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.1f} MB"

        file_io = io.BytesIO(content)
        file_io.name = filename

        await msg.reply_document(
            document=file_io,
            filename=filename,
            caption=(
                f"✅ *Archivo descargado*\n\n"
                f"📄 Nombre: `{filename}`\n"
                f"📦 Tamaño: `{size_str}`\n"
                f"🔗 Fuente: [Link]({url})"
            ),
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    except requests.exceptions.Timeout:
        await msg.reply_text("❌ Tiempo de espera agotado.", reply_markup=main_menu_keyboard())
    except requests.exceptions.HTTPError as e:
        await msg.reply_text(f"❌ Error HTTP: `{e}`", parse_mode='Markdown', reply_markup=main_menu_keyboard())
    except Exception as e:
        await msg.reply_text(f"❌ Error: `{str(e)}`", parse_mode='Markdown', reply_markup=main_menu_keyboard())

    return ConversationHandler.END
