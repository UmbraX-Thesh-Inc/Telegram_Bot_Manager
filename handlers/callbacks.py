from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import main_menu_keyboard
from utils.github_api import get_user_info, list_branches


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # ── Main menu ──────────────────────────────────────────────────────────────
    if data == 'main_menu':
        await query.answer()
        from handlers.start import start_handler
        gh_info, _ = get_user_info()
        gh_name = gh_info.get('login', 'N/A')
        gh_repos = gh_info.get('public_repos', 0)
        user = query.from_user
        text = (
            f"╔══════════════════════════╗\n"
            f"  🤖 *GitHub Manager Bot*\n"
            f"╚══════════════════════════╝\n\n"
            f"👋 ¡Hola, *{user.first_name}*!\n\n"
            f"🐙 GitHub: `@{gh_name}`\n"
            f"📁 Repositorios: `{gh_repos}`\n\n"
            f"*¿Qué deseas hacer hoy?*"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
        return

    # ── Help ───────────────────────────────────────────────────────────────────
    if data == 'help':
        await query.answer()
        from handlers.start import help_handler
        text = (
            "╔══════════════════════════╗\n"
            "  ❓ *Ayuda - GitHub Bot*\n"
            "╚══════════════════════════╝\n\n"
            "📋 *Funciones disponibles:*\n\n"
            "📁 *Mis Repos* — Lista tus repositorios\n"
            "➕ *Crear Repo* — Crea un nuevo repositorio\n"
            "🔍 *Buscar Repos* — Busca en GitHub\n"
            "🍴 *Forkear* — Haz fork de cualquier repo\n"
            "📤 *Subir Archivos* — Sube archivos a un repo\n"
            "📥 *Descargar ZIP* — Descarga repos como ZIP\n"
            "✏️ *Editar* — Edita archivos de tus repos\n"
            "🗑️ *Eliminar* — Elimina repositorios\n"
            "🤖 *IA Gemini* — Chat con inteligencia artificial\n"
            "🌐 *Descargar URL* — Descarga archivos por link\n\n"
            "💡 Usa /start para volver al menú principal"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
        return

    # ── GitHub Profile ─────────────────────────────────────────────────────────
    if data == 'gh_profile':
        await query.answer()
        info, status = get_user_info()
        if status == 200:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            text = (
                f"╔══════════════════╗\n"
                f"  👤 *Perfil GitHub*\n"
                f"╚══════════════════╝\n\n"
                f"🐙 Usuario: `{info.get('login', 'N/A')}`\n"
                f"📛 Nombre: `{info.get('name', 'N/A')}`\n"
                f"📧 Email: `{info.get('email', 'No público')}`\n"
                f"🏢 Empresa: `{info.get('company', 'N/A')}`\n"
                f"🌍 Ubicación: `{info.get('location', 'N/A')}`\n"
                f"📁 Repos públicos: `{info.get('public_repos', 0)}`\n"
                f"👥 Seguidores: `{info.get('followers', 0)}`\n"
                f"👣 Siguiendo: `{info.get('following', 0)}`\n"
                f"📅 Miembro desde: `{info.get('created_at', 'N/A')[:10]}`\n"
                f"🔗 [Ver en GitHub]({info.get('html_url', '')})"
            )
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
        else:
            await query.edit_message_text("❌ Error obteniendo perfil.", reply_markup=main_menu_keyboard())
        return

    # ── List repos ─────────────────────────────────────────────────────────────
    if data == 'list_repos':
        from handlers.github_repos import list_repos_handler
        await list_repos_handler(update, context, page=1)
        return

    if data.startswith('repos_page_'):
        page = int(data.replace('repos_page_', ''))
        from handlers.github_repos import list_repos_handler
        await list_repos_handler(update, context, page=page)
        return

    # ── Repo info ──────────────────────────────────────────────────────────────
    if data.startswith('repo_'):
        parts = data.replace('repo_', '').split('_', 1)
        owner = parts[0] if len(parts) > 1 else ''
        repo = parts[1] if len(parts) > 1 else parts[0]
        from handlers.github_repos import repo_info_handler
        await repo_info_handler(update, context, owner, repo)
        return

    if data.startswith('repoinfo_'):
        full_name = data.replace('repoinfo_', '').replace('_', '/', 1)
        parts = full_name.split('/', 1)
        owner = parts[0]
        repo = parts[1] if len(parts) > 1 else parts[0]
        from handlers.github_repos import repo_info_handler
        await repo_info_handler(update, context, owner, repo)
        return

    # ── Delete repo ────────────────────────────────────────────────────────────
    if data == 'delete_repo_menu':
        from handlers.github_repos import delete_repo_handler
        await delete_repo_handler(update, context)
        return

    if data.startswith('delconfirm_'):
        await query.answer()
        repo = data.replace('delconfirm_', '')
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚠️ Sí, eliminar '{repo}'", callback_data=f'delexec_{repo}')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='main_menu')]
        ])
        await query.edit_message_text(
            f"⚠️ *¿Confirmar eliminación?*\n\n"
            f"🗑️ Repo: `{repo}`\n\n"
            f"_Esta acción no se puede deshacer._",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return

    if data.startswith('delexec_'):
        repo = data.replace('delexec_', '')
        from handlers.github_repos import delete_repo_handler
        await delete_repo_handler(update, context, repo)
        return

    # ── ZIP download ───────────────────────────────────────────────────────────
    if data.startswith('zip_') or data.startswith('zipdl_'):
        from handlers.github_download import download_zip_handler
        await download_zip_handler(update, context)
        return

    # ── File browser ───────────────────────────────────────────────────────────
    if data.startswith('files_'):
        parts = data.split('_')
        owner = parts[1] if len(parts) > 1 else ''
        repo = parts[2] if len(parts) > 2 else ''
        path = '_'.join(parts[3:]) if len(parts) > 3 else ''
        from handlers.github_download import list_files_handler
        await list_files_handler(update, context, owner, repo, path)
        return

    if data.startswith('dlfile_'):
        parts = data.replace('dlfile_', '').split('_')
        owner = parts[0]
        repo = parts[1]
        path = '/'.join(parts[2:])
        from handlers.github_download import download_file_handler
        await download_file_handler(update, context, owner, repo, path)
        return

    # ── Branches ───────────────────────────────────────────────────────────────
    if data.startswith('branches_'):
        await query.answer()
        parts = data.replace('branches_', '').split('_', 1)
        owner = parts[0]
        repo = parts[1] if len(parts) > 1 else ''
        branches, status = list_branches(owner, repo)
        if status == 200:
            branch_list = '\n'.join([f"• `{b['name']}`" for b in branches])
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            await query.edit_message_text(
                f"🌿 *Branches de {owner}/{repo}:*\n\n{branch_list}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Menú", callback_data='main_menu')]
                ])
            )
        else:
            await query.edit_message_text("❌ Error obteniendo branches.", reply_markup=main_menu_keyboard())
        return

    # ── Upload to repo ─────────────────────────────────────────────────────────
    if data.startswith('uploadto_'):
        from handlers.github_upload import upload_handler
        await upload_handler(update, context)
        return

    # ── Edit desc ──────────────────────────────────────────────────────────────
    if data.startswith('editdesc_'):
        from handlers.github_edit import edit_repo_handler
        await edit_repo_handler(update, context)
        return

    # ── Edit actions ───────────────────────────────────────────────────────────
    if data.startswith('editsel_') or data.startswith('editaction_') or data.startswith('editfile_'):
        from handlers.github_edit import edit_repo_handler
        await edit_repo_handler(update, context)
        return

    # Fallback
    await query.answer("⚠️ Acción no reconocida")
