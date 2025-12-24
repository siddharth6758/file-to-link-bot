import os
import requests
from flask import Flask, request, abort, Response
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
        abort(403, "Link expired")

    tg = requests.get(
        f"{TG_API}/getFile",
        params={"file_id": file_id}
    ).json()

    path = tg["result"]["file_path"]

    video = requests.get(
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}",
        stream=True
    )

    return Response(
        video.iter_content(chunk_size=1024 * 1024),
        content_type="video/mp4"
    )

asgi_app = WsgiToAsgi(app)