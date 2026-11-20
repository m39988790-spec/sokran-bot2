import logging
import os
import threading

import requests
from flask import Flask, request

from config import BOT_TOKEN, PORT, WEBHOOK_PATH, RENDER_EXTERNAL_URL
from keyboards import quality_keyboard
from downloader import download_media, validate_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = Flask(__name__)


def telegram(method, data=None, files=None):
    response = requests.post(
        f"{API}/{method}",
        data=data,
        files=files,
        timeout=600
    )
    response.raise_for_status()
    return response.json()


def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        import json
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    telegram("sendMessage", payload)


def answer_callback(callback_id, text=""):
    telegram("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


def send_media(chat_id, file_path, media_kind):
    with open(file_path, "rb") as media_file:
        if media_kind == "audio":
            telegram(
                "sendAudio",
                {"chat_id": chat_id, "title": os.path.basename(file_path)},
                {"audio": media_file}
            )
        else:
            telegram(
                "sendDocument",
                {"chat_id": chat_id, "caption": "تم تجهيز الملف 🎬"},
                {"document": media_file}
            )


def handle_download(chat_id, url, quality):
    send_message(chat_id, "⏳ جاري تجهيز طلبك، قد يستغرق ذلك بعض الوقت...")
    try:
        result_path, media_kind = download_media(url, quality)
        send_media(chat_id, result_path, media_kind)
    except Exception as exc:
        logger.exception("Media download failed: %s", exc)
        send_message(
            chat_id,
            "تعذر تجهيز هذا الرابط. تأكد أن الموقع مدعوم وأن المحتوى متاح "
            "للتنزيل، أو جرّب جودة أقل."
        )


@app.get("/")
def health():
    return "Media bot is running", 200


@app.post(WEBHOOK_PATH)
def webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message")
    if message:
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "أهلاً بك في بوت تحميل الوسائط 🎬\n\n"
                "أرسل رابط فيديو من موقع مدعوم، ثم اختر دقة الفيديو "
                "أو استخراج الصوت فقط.\n\n"
                "تم إنشاء هذا البوت بواسطة محمد عايض."
            )
        elif text.startswith("/help"):
            send_message(
                chat_id,
                "طريقة الاستخدام:\n"
                "1- أرسل رابط الفيديو.\n"
                "2- اختر الدقة المناسبة أو الصوت فقط.\n\n"
                "تختلف المواقع والجودات المتاحة حسب الفيديو الأصلي."
            )
        elif text.startswith("https://") or text.startswith("http://"):
            if validate_url(text):
                send_message(chat_id, "اختر ما تريد:", quality_keyboard(text))
            else:
                send_message(chat_id, "هذا الرابط غير صالح أو غير مدعوم.")
        else:
            send_message(chat_id, "أرسل رابط فيديو صحيحًا يبدأ بـ https://")

    callback = update.get("callback_query")
    if callback:
        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data", "")
        answer_callback(callback["id"], "تم استلام طلبك")

        parts = data.split("|", 1)
        if len(parts) == 2:
            quality, url = parts
            if validate_url(url):
                threading.Thread(
                    target=handle_download,
                    args=(chat_id, url, quality),
                    daemon=True
                ).start()
            else:
                send_message(chat_id, "انتهت صلاحية الرابط أو أنه غير صالح.")

    return "OK", 200


def register_webhook():
    if RENDER_EXTERNAL_URL:
        webhook_url = RENDER_EXTERNAL_URL.rstrip("/") + WEBHOOK_PATH
        telegram("setWebhook", {"url": webhook_url})
        logger.info("Telegram webhook registered")


if __name__ == "__main__":
    register_webhook()
    app.run(host="0.0.0.0", port=PORT)
