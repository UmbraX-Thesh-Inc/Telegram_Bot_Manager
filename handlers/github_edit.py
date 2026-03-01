from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import (
    get_repo_contents, get_file_content, update_file_content,
    update_repo_settings, list_repositories, list_branches, create_branch
)
from utils.keyboards import main_menu_keyboard, back_keyboard
from handlers.states import EDIT_REPO, EDIT_FILE, EDIT_CONTENT
import base64


async def edit_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'edit_repo':
        await query.answer()
        repos, _ = list_repositories()
        keyboard = []
        for r in repos:
            owner = r['owner']['login']
            keyboard.append([InlineKeyboardButton(
                f"📁 {r['name']}",
                callback_data=f'editsel_{owner}_{r["name"]}'
            )])
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "✏️ *Editar Repositorio*\n\nSelecciona el repo:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_REPO

    if query and query.data.startswith('editsel_'):
        await query.answer()
        parts = query.data.replace('editsel_', '').rsplit('_', 1)
        owner = parts[0] if len(parts) > 1 else ''
        repo = parts[1] if len(parts) > 1 else parts[0]
        context.user_data['edit_owner'] = owner
        context.user_data['edit_repo'] = repo

        keyboard = [
            [InlineKeyboardButton("📝 Editar Archivo", callback_data='editaction_file')],
            [InlineKeyboardButton("📄 Editar Descripción", callback_data='editaction_desc')],
            [InlineKeyboardButton("🌿 Crear Branch", callback_data='editaction_branch')],
            [InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')]
        ]
        await query.edit_message_text(
            f"✏️ *Editando:* `{owner}/{repo}`\n\n¿Qué deseas hacer?",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_FILE

    # Subacciones
    if query and query.data == 'editaction_file':
        await query.answer()
        owner = context.user_data.get('edit_owner', '')
        repo = context.user_data.get('edit_repo', '')
        contents, _ = get_repo_contents(owner, repo)
        keyboard = []
        for item in contents[:15]:
            if item['type'] == 'file':
                keyboard.append([InlineKeyboardButton(
                    f"📄 {item['name']}",
                    callback_data=f'editfile_{item["path"]}'
                )])
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "📄 Selecciona el archivo a editar:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_FILE

    if query and query.data.startswith('editfile_'):
        await query.answer()
        file_path = query.data.replace('editfile_', '')
        owner = context.user_data.get('edit_owner', '')
        repo = context.user_data.get('edit_repo', '')
        result, status = get_file_content(owner, repo, file_path)
        if status != 200:
            await query.edit_message_text("❌ Error obteniendo archivo.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END

        content_b64 = result.get('content', '')
        try:
            current_content = base64.b64decode(content_b64).decode('utf-8')
        except Exception:
            current_content = '[Archivo binario, no editable]'

        context.user_data['edit_file_path'] = file_path
        context.user_data['edit_file_sha'] = result.get('sha', '')

        preview = current_content[:500] + ('...' if len(current_content) > 500 else '')
        await query.edit_message_text(
            f"📄 *Archivo:* `{file_path}`\n\n"
            f"*Contenido actual:*\n```\n{preview}\n```\n\n"
            f"Escribe el *nuevo contenido completo* del archivo:",
            parse_mode='Markdown'
        )
        return EDIT_CONTENT

    if query and query.data == 'editaction_desc':
        await query.answer()
        await query.edit_message_text(
            "📝 Escribe la *nueva descripción* del repositorio:",
            parse_mode='Markdown'
        )
        context.user_data['edit_action'] = 'desc'
        return EDIT_CONTENT

    if query and query.data == 'editaction_branch':
        await query.answer()
        await query.edit_message_text(
            "🌿 Escribe el *nombre del nuevo branch*:",
            parse_mode='Markdown'
        )
        context.user_data['edit_action'] = 'branch'
        return EDIT_CONTENT

    # editdesc_ from repo actions
    if query and query.data.startswith('editdesc_'):
        await query.answer()
        repo = query.data.replace('editdesc_', '')
        context.user_data['edit_repo'] = repo
        context.user_data['edit_action'] = 'desc'
        await query.edit_message_text(
            f"📝 Escribe la nueva descripción para `{repo}`:",
            parse_mode='Markdown'
        )
        return EDIT_CONTENT

    msg = update.message
    if msg:
        await msg.reply_text("✏️ Usa el menú para editar.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END


async def edit_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return ConversationHandler.END

    new_content = msg.text
    edit_action = context.user_data.get('edit_action', 'file')
    repo = context.user_data.get('edit_repo', '')
    owner = context.user_data.get('edit_owner', '')

    if edit_action == 'desc':
        result, status = update_repo_settings(repo, description=new_content)
        if status == 200:
            await msg.reply_text(
                f"✅ Descripción de `{repo}` actualizada.",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await msg.reply_text(f"❌ Error: `{result.get('message', 'Error')}`",
                                 parse_mode='Markdown', reply_markup=main_menu_keyboard())

    elif edit_action == 'branch':
        result, status = create_branch(repo, new_content)
        if status == 201:
            await msg.reply_text(
                f"✅ Branch `{new_content}` creado en `{repo}`.",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await msg.reply_text(f"❌ Error: `{result.get('message', 'Error')}`",
                                 parse_mode='Markdown', reply_markup=main_menu_keyboard())

    else:
        # Editar archivo
        file_path = context.user_data.get('edit_file_path', '')
        sha = context.user_data.get('edit_file_sha', '')
        await msg.reply_text("⏳ Guardando cambios...")
        result, status = update_file_content(repo, file_path, new_content, sha)
        if status in (200, 201):
            url = result.get('content', {}).get('html_url', '')
            await msg.reply_text(
                f"✅ *Archivo actualizado:*\n`{file_path}`\n"
                f"🔗 [Ver en GitHub]({url})",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            err = result.get('message', 'Error')
            await msg.reply_text(
                f"❌ Error al guardar:\n`{err}`",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )

    context.user_data.clear()
    return ConversationHandler.END
