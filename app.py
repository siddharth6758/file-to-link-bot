import os
import requests
from flask import Flask, request, abort, Response, stream_with_context
from token_utils import generate_token, verify_token
from asgiref.wsgi import WsgiToAsgi

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DOMAIN_URL = f"https://www.freetelebotfiletolink.publicvm.com/"

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")

    file_id = None
    media_type = None

    if "video" in msg:
        file_id = msg["video"]["file_id"]
        media_type = "video"

    elif "photo" in msg:
        # highest resolution photo
        file_id = msg["photo"][-1]["file_id"]
        media_type = "image"

    elif "animation" in msg:  # GIF
        file_id = msg["animation"]["file_id"]
        media_type = "gif"

    elif "document" in msg:
        file_id = msg["document"]["file_id"]
        media_type = "document"

    else:
        return {"ok": True}

    token = generate_token(file_id, media_type)
    watch_url = f"{DOMAIN_URL}watch?token={token}"

    requests.post(f"{TG_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"Secure link (valid 5 minutes):\n{watch_url}"
    })

    return {"ok": True}


@app.route("/watch")
def watch():
    token = request.args.get("token")
    data = verify_token(token)

    if not data:
        abort(403, "Expired or invalid link")

    file_id = data["file_id"]
    media_type = data["media_type"]

    # Get file path from Telegram
    tg = requests.get(
        f"{TG_API}/getFile",
        params={"file_id": file_id},
        timeout=10
    ).json()

    path = tg["result"]["file_path"]

    tg_stream = requests.get(
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}",
        stream=True,
        timeout=30
    )

    # Map media type to browser content type
    content_types = {
        "video": "video/mp4",
        "gif": "image/gif",
        "image": "image/jpeg",
        "document": "application/octet-stream"
    }

    content_type = content_types.get(media_type, "application/octet-stream")

    def generate():
        for chunk in tg_stream.iter_content(chunk_size=1024 * 256):
            if chunk:
                yield chunk

    return Response(
        stream_with_context(generate()),
        content_type=content_type,
        headers={
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
            "X-Content-Type-Options": "nosniff"
        }
    )


asgi_app = WsgiToAsgi(app)