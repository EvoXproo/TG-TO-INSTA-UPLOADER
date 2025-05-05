import os
import logging
import yt_dlp
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import BotCommand, Update
import yt_dlp
from instagrapi import Client
import pytz

# Telegram bot ka initial setup
BOT_TOKEN = "7023532002:AAH0CIoVrugmVrGozFPIxZcn0KZbQy5XGQo"  # Yahan apna Telegram Bot Token daalein
INSTAGRAM_USERNAME = "weird_hub_facts"  # Instagram username
INSTAGRAM_PASSWORD = "aryan@2007"  # Instagram password

# Ensure downloads folder exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Global state
USE_CUSTOM_THUMBNAIL = {"enabled": False}
AUTO_MODE = {"enabled": False}
USER_SESSION = {}  # per user: {"awaiting_caption": False, "video_path": ..., "default_caption": ...}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "𝙄𝙣𝙨𝙩𝙖𝙜𝙧𝙖𝙢 𝙍𝙚𝙚𝙡 𝘿𝙤𝙬𝙣𝙡𝙤𝙖𝙙𝙚𝙧 𝙍𝙚𝙖𝙙𝙮!\n"
        "\n"
        "Commands:\n\n"
        "💫 `/auto on` :- 𝙥𝙤𝙨𝙩 𝙘𝙖𝙥𝙩𝙞𝙤𝙣 𝙖𝙨 𝙞𝙩 𝙞𝙨..!!\n\n"
        "⚡️ `/auto off` : 𝙘𝙪𝙨𝙩𝙤𝙢𝙞𝙯𝙚 𝙘𝙖𝙥𝙩𝙞𝙤𝙣\n\n"
        "🍄 `/set` :- 𝙨𝙚𝙩 𝙘𝙪𝙧𝙧𝙚𝙣𝙩 𝙥𝙝𝙤𝙩𝙤 𝙖𝙨 𝙙𝙚𝙛𝙖𝙪𝙡𝙩 𝙩𝙝𝙪𝙢𝙗𝙣𝙖𝙞𝙡\n\n"
        "✅ `/thumbnail on` :- 𝙨𝙮𝙨𝙩𝙚𝙢 𝙩𝙝𝙪𝙢𝙗𝙣𝙖𝙞𝙡 𝙪𝙥𝙡𝙤𝙖𝙙𝙨\n\n"
        "♻️ `/thumbnail off` :- 𝙥𝙤𝙨𝙩 𝙘𝙖𝙥𝙩𝙞𝙤𝙣 𝙖𝙨 𝙞𝙩 𝙞𝙨..!!\n"
        "\n"
        "𝙎𝙞𝙢𝙥𝙡𝙮 𝙨𝙚𝙣𝙙 𝙖 𝙡𝙞𝙣𝙠 𝙩𝙤 𝙗𝙚𝙜𝙞𝙣.",
        parse_mode="Markdown")

def download_reel(link):
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'format': 'best',
        'quiet': True,
        'cookiefile': 'cookies.txt',  # ✅ Added cookies support
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            video_path = f"downloads/{info['id']}.{info['ext']}"
            caption = info.get('description', 'No caption available')
            return video_path, caption
    except Exception as e:
        return None, f"Download error: {str(e)}"

def upload_to_instagram(video_path, caption):
    try:
        import moviepy
        if moviepy.__version__ < '1.0.3':
            return "Error: moviepy version must be >= 1.0.3. Please upgrade moviepy."

        cl = Client()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)

        if USE_CUSTOM_THUMBNAIL["enabled"] and os.path.exists("thumbnail.png"):
            cl.clip_upload(video_path, caption=caption, thumbnail="thumbnail.png")
        else:
            cl.clip_upload(video_path, caption=caption)

        return "✅ Successfully uploaded to Instagram!"
    except Exception as e:
        return f"Upload error: {str(e)}"

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_text = (update.message.text or update.message.caption or "").strip()
    
    # 📸 Photo with caption '/set' → save as thumbnail
    if update.message.photo and update.message.caption and update.message.caption.strip() == "/set":
        file = await update.message.photo[-1].get_file()
        await file.download_to_drive("thumbnail.png")
        USE_CUSTOM_THUMBNAIL["enabled"] = True
        await update.message.reply_text("✅ Thumbnail updated and set to ON (saved as thumbnail.png)")
        return

    if message_text.lower() == "/thumbnail on":
        USE_CUSTOM_THUMBNAIL["enabled"] = True
        await update.message.reply_text("📸 Thumbnail mode: ON. Make sure 'thumbnail.png' exists.")
        return

    elif message_text.lower() == "/thumbnail off":
        USE_CUSTOM_THUMBNAIL["enabled"] = False
        await update.message.reply_text("📸 Thumbnail mode: OFF. Using default thumbnail.")
        return

    elif message_text.lower() == "/auto on":
        AUTO_MODE["enabled"] = True
        await update.message.reply_text("🚀 Auto mode: ON. Just send links to auto-upload.")
        return

    elif message_text.lower() == "/auto off":
        AUTO_MODE["enabled"] = False
        await update.message.reply_text("⚙️ Auto mode: OFF. Now you'll be asked to enter captions.")
        return

    # If user is expected to send caption
    if user_id in USER_SESSION and USER_SESSION[user_id].get("awaiting_caption"):
        caption = message_text
        video_path = USER_SESSION[user_id]["video_path"]

        if not os.path.exists(video_path):
            await update.message.reply_text("❗ Video file not found. Please start again.")
            del USER_SESSION[user_id]
            return

        result = upload_to_instagram(video_path, caption)
        await update.message.reply_text(result)
        os.remove(video_path)
        del USER_SESSION[user_id]
        return

    # If a link is sent
    if "instagram.com/reel/" in message_text:
        link = message_text
        await update.message.reply_text("⬇️ Downloading reel...")

        video_path, default_caption = download_reel(link)
        if not video_path:
            await update.message.reply_text(default_caption)
            return

        if AUTO_MODE["enabled"]:
            await update.message.reply_text("📤 Uploading with default caption...")
            result = upload_to_instagram(video_path, default_caption)
            await update.message.reply_text(result)
            os.remove(video_path)
        else:
            USER_SESSION[user_id] = {
                "awaiting_caption": True,
                "video_path": video_path,
                "default_caption": default_caption
            }
            await update.message.reply_text(f"📝 Default Caption:\n{default_caption}\n\nPlease reply with your caption to upload.")
        return

    await update.message.reply_text("❗ Unknown command or message. Use /start to see available commands.")

async def set_bot_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Show welcome/help message"),
        BotCommand("auto", "Toggle auto mode (on/off)"),
        BotCommand("thumbnail", "Toggle thumbnail mode (on/off)"),
    ])

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/set$'), handle_message))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.post_init = set_bot_commands
    application.run_polling(allowed_updates=["message"])

if __name__ == '__main__':
    main()
