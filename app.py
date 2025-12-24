import os
import requests
from flask import Flask, request, abort, Response, stream_with_context
from token_utils import generate_token, verify_token
from asgiref.wsgi import WsgiToAsgi

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    msg = update.get("message", {})

    if "video" not in msg:
        return {"ok": True}

    file_id = msg["video"]["file_id"]
    chat_id = msg["chat"]["id"]

    token = generate_token(file_id)
    watch_url = f"{request.url_root}watch?token={token}"

    requests.post(f"{TG_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"Secure video link (valid 5 minutes):\n{watch_url}"
    })

    return {"ok": True}


@app.route("/watch")
def watch():
    token = request.args.get("token")
    file_id = verify_token(token)

    if not file_id:
        abort(403, "Expired")

    tg = requests.get(
        f"{TG_API}/getFile",
        params={"file_id": file_id},
        timeout=10
    ).json()

    if "result" not in tg:
        abort(500, "Telegram getFile failed")

    path = tg["result"]["file_path"]

    tg_stream = requests.get(
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}",
        stream=True,
        timeout=30
    )

    def generate():
        for chunk in tg_stream.iter_content(chunk_size=1024 * 256):
            if chunk:
                yield chunk

    return Response(
        stream_with_context(generate()),
        mimetype="video/mp4",
        headers={
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
            "X-Content-Type-Options": "nosniff"
        }
    )

asgi_app = WsgiToAsgi(app)