import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler, ContextTypes
)
from config.settings import BOT_TOKEN
from handlers.start import start_handler, help_handler
from handlers.github_repos import (
    create_repo_handler, list_repos_handler, search_repos_handler,
    fork_repo_handler, delete_repo_handler, repo_info_handler
)
from handlers.github_upload import upload_handler, upload_file_handler
from handlers.github_download import download_zip_handler, download_file_handler
from handlers.github_edit import edit_repo_handler, edit_file_handler
from handlers.ai_handler import ai_chat_handler
from handlers.url_download import url_download_handler
from handlers.callbacks import callback_handler
from handlers.states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Handlers async para acceso no autorizado ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Conversación cancelada.")
    return ConversationHandler.END

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # --- Conversaciones ---
    create_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_repo_handler, pattern='^create_repo$')],
        states={
            REPO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_repo_handler)],
            REPO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_repo_handler)],
            REPO_PRIVATE: [CallbackQueryHandler(create_repo_handler, pattern='^(public|private)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    fork_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(fork_repo_handler, pattern='^fork_repo$')],
        states={FORK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, fork_repo_handler)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    upload_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(upload_handler, pattern='^upload_repo$')],
        states={
            UPLOAD_REPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_handler)],
            UPLOAD_FILE: [MessageHandler(filters.Document.ALL | filters.TEXT, upload_file_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    zip_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(download_zip_handler, pattern='^download_zip$')],
        states={ZIP_REPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_zip_handler)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    ai_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ai_chat_handler, pattern='^ai_chat$')],
        states={AI_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_repos_handler, pattern='^search_repo$')],
        states={SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_repos_handler)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    url_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(url_download_handler, pattern='^url_download$')],
        states={URL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, url_download_handler)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_repo_handler, pattern='^edit_repo$')],
        states={
            EDIT_REPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_repo_handler)],
            EDIT_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_file_handler)],
            EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_file_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # --- Comandos ---
    app.add_handler(CommandHandler('start', start_handler))
    app.add_handler(CommandHandler('help', help_handler))

    # --- Agregar conversaciones ---
    app.add_handler(create_conv)
    app.add_handler(fork_conv)
    app.add_handler(upload_conv)
    app.add_handler(zip_conv)
    app.add_handler(ai_conv)
    app.add_handler(search_conv)
    app.add_handler(url_conv)
    app.add_handler(edit_conv)

    # --- Callbacks ---
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Bot iniciado en modo polling...")

    # --- Ejecutar polling ---
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
