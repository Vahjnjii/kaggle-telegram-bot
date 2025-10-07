"""
🤖 Kaggle Telegram Bot - Render.com (FIXED VERSION)
Runs 24/7 on Render cloud servers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import os
import json
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CREDENTIALS ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8412746575:AAHvXPg13EO9KJE2LRxmBeHQByT8lQuc3m4')
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME', 'shreevathsbbhh')
KAGGLE_KEY = os.getenv('KAGGLE_KEY', '89460e94583028e66c749dc72e03b450')
NOTEBOOK_SLUG = os.getenv('NOTEBOOK_SLUG', 'shreevathsbbhh/app-1-5')
# ====================================================

# Global state
notebook_state = {
    'is_running': False,
    'start_time': None,
    'task': None,
    'last_status': 'stopped'
}


def setup_kaggle():
    """Setup Kaggle credentials"""
    try:
        kaggle_dir = os.path.expanduser("~/.kaggle")
        os.makedirs(kaggle_dir, exist_ok=True)
        
        kaggle_json = os.path.join(kaggle_dir, "kaggle.json")
        with open(kaggle_json, 'w') as f:
            json.dump({"username": KAGGLE_USERNAME, "key": KAGGLE_KEY}, f, indent=2)
        
        try:
            os.chmod(kaggle_json, 0o600)
        except:
            pass
        
        logger.info("✅ Kaggle configured")
        return True
    except Exception as e:
        logger.error(f"❌ Kaggle error: {e}")
        return False


async def execute_notebook():
    """Execute Kaggle notebook"""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        api.authenticate()
        
        logger.info(f"🚀 Starting: {NOTEBOOK_SLUG}")
        api.kernels_push(NOTEBOOK_SLUG)
        notebook_state['last_status'] = 'running'
        logger.info("✅ Started!")
        
        check = 0
        while notebook_state['is_running']:
            await asyncio.sleep(30)
            check += 1
            
            try:
                status = api.kernels_status(NOTEBOOK_SLUG).get('status', 'unknown')
                logger.info(f"[{check}] {status}")
                notebook_state['last_status'] = status
                
                if status in ['complete', 'error', 'cancelAcknowledged', 'cancelled']:
                    logger.info(f"✅ {status}")
                    notebook_state['is_running'] = False
                    break
            except Exception as e:
                logger.warning(f"Check error: {e}")
                await asyncio.sleep(30)
        
        logger.info("⏹️ Stopped")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        notebook_state['is_running'] = False
        notebook_state['last_status'] = 'error'


def get_emoji(status):
    """Get status emoji"""
    emojis = {
        'running': '🟢', 'complete': '✅', 'error': '❌',
        'stopped': '🔴', 'queued': '🟡', 'unknown': '⚪'
    }
    return emojis.get(status.lower(), '⚪')


def format_time():
    """Format runtime"""
    if notebook_state['start_time']:
        elapsed = time.time() - notebook_state['start_time']
        return f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    return "Not started"


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start"""
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start", callback_data='start'),
            InlineKeyboardButton("⏹️ Stop", callback_data='stop')
        ],
        [InlineKeyboardButton("📊 Status", callback_data='status')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    
    await update.message.reply_text(
        f"🤖 *Kaggle Bot*\n\n"
        f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
        f"👤 `{KAGGLE_USERNAME}`\n"
        f"☁️ Running on Render\n\n"
        "Control your notebook:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start':
        if notebook_state['is_running']:
            keyboard = [
                [InlineKeyboardButton("⏹️ Stop", callback_data='stop')],
                [InlineKeyboardButton("📊 Status", callback_data='status')]
            ]
            await query.edit_message_text(
                f"⚠️ *Already Running!*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"⏰ `{format_time()}`\n"
                f"📊 🟢 Running",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            notebook_state['is_running'] = True
            notebook_state['start_time'] = time.time()
            notebook_state['task'] = asyncio.create_task(execute_notebook())
            
            keyboard = [
                [InlineKeyboardButton("⏹️ Stop", callback_data='stop')],
                [InlineKeyboardButton("📊 Status", callback_data='status')]
            ]
            await query.edit_message_text(
                f"✅ *Started!*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"👤 `{KAGGLE_USERNAME}`\n"
                f"⏰ `{datetime.now().strftime('%H:%M:%S')}`\n"
                f"📊 🟢 Running on Kaggle\n\n"
                "Notebook executing!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    elif query.data == 'stop':
        if not notebook_state['is_running']:
            keyboard = [
                [InlineKeyboardButton("▶️ Start", callback_data='start')],
                [InlineKeyboardButton("📊 Status", callback_data='status')]
            ]
            await query.edit_message_text(
                f"ℹ️ *Not Running*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"📊 🔴 Stopped",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            notebook_state['is_running'] = False
            if notebook_state['task']:
                notebook_state['task'].cancel()
            
            keyboard = [
                [InlineKeyboardButton("▶️ Start", callback_data='start')],
                [InlineKeyboardButton("📊 Status", callback_data='status')]
            ]
            await query.edit_message_text(
                f"⏹️ *Stopped*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"⏰ `{format_time()}`\n"
                f"📊 🔴 Monitoring stopped\n\n"
                f"⚠️ May still run on Kaggle",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    elif query.data == 'status':
        status = notebook_state['last_status']
        emoji = get_emoji(status)
        running = notebook_state['is_running']
        
        keyboard = [
            [
                InlineKeyboardButton("▶️", callback_data='start'),
                InlineKeyboardButton("⏹️", callback_data='stop')
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data='status')]
        ]
        
        if running:
            text = (
                f"📊 *Status*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"⏰ `{format_time()}`\n"
                f"📊 {emoji} {status.upper()}\n"
                f"🔗 Monitoring: ✅\n\n"
                f"`{datetime.now().strftime('%H:%M:%S')}`"
            )
        else:
            text = (
                f"📊 *Status*\n\n"
                f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
                f"📊 🔴 STOPPED\n"
                f"🔗 Monitoring: ❌\n\n"
                f"`{datetime.now().strftime('%H:%M:%S')}`"
            )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'help':
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data='back')]]
        await query.edit_message_text(
            "ℹ️ *Help*\n\n"
            "▶️ *Start* - Run notebook\n"
            "⏹️ *Stop* - Stop monitoring\n"
            "📊 *Status* - Check status\n\n"
            "📝 *Info:*\n"
            "• Bot runs 24/7 on Render\n"
            "• Real-time monitoring\n"
            "• 9-hour Kaggle limit\n\n"
            f"🔗 [Notebook](https://www.kaggle.com/code/{NOTEBOOK_SLUG})",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'back':
        keyboard = [
            [
                InlineKeyboardButton("▶️ Start", callback_data='start'),
                InlineKeyboardButton("⏹️ Stop", callback_data='stop')
            ],
            [InlineKeyboardButton("📊 Status", callback_data='status')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        await query.edit_message_text(
            f"🤖 *Kaggle Bot*\n\n"
            f"📓 `{NOTEBOOK_SLUG.split('/')[-1]}`\n"
            f"☁️ Running on Render",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception: {context.error}")


async def post_init(application: Application):
    """Post init callback"""
    logger.info("✅ Bot initialized")


def main():
    """Main function"""
    logger.info("="*60)
    logger.info("🤖 KAGGLE BOT STARTING")
    logger.info("="*60)
    
    if not setup_kaggle():
        logger.error("Setup failed")
        return
    
    logger.info(f"📓 {NOTEBOOK_SLUG}")
    logger.info(f"👤 {KAGGLE_USERNAME}")
    logger.info(f"☁️ Render.com")
    
    try:
        # Build application with proper configuration
        application = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .post_init(post_init)
            .build()
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_cmd))
        application.add_handler(CallbackQueryHandler(button_click))
        application.add_error_handler(error_handler)
        
        logger.info("="*60)
        logger.info("✅ BOT RUNNING 24/7!")
        logger.info("="*60)
        logger.info("📱 @vathsas_bot")
        logger.info("="*60)
        
        # Run with proper settings
        application.run_polling(
            poll_interval=1.0,
            timeout=10,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
