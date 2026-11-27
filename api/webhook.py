import os
import json
import requests
from flask import Flask, request, jsonify
from prices_engine import suformuoti_zinute, miestu_klaviatura, keisti_miesta_mygtukas

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
TG_API = f"https://telegram.org{BOT_TOKEN}"

def redis_cmd(args):
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    r = requests.post(
        REDIS_URL,
        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        json=args,
        timeout=10
    )
    return r.json().get("result") if r.ok else None

def issaugoti_vartotojo_miesta(chat_id, miestas):
    redis_cmd(["HSET", "ev_fuel_users", str(chat_id), miestas])

def gauti_vartotojo_miesta(chat_id):
    res = redis_cmd(["HGET", "ev_fuel_users", str(chat_id)])
    return res if res else "Visa Lietuva"

def siusti_tg(method, payload):
    requests.post(f"{TG_API}/{method}", json=payload, timeout=10)

@app.route("/", defaults={"path": ""}, methods=["POST", "GET"])
@app.route("/<path:path>", methods=["POST", "GET"])
def webhook(path=""):
    if request.method == "GET":
        return "Telegram botas veikia!", 200

    update = request.get_json(silent=True) or {}

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.startswith("/start") or text.startswith("/miestas"):
            esamas_miestas = gauti_vartotojo_miesta(chat_id)
            issaugoti_vartotojo_miesta(chat_id, esamas_miestas)
            siusti_tg("sendMessage", {
                "chat_id": chat_id,
                "text": f"Sveiki! 👋 Kas rytą 08:00 val. atsiųsiu mažiausias degalų ir EV įkrovimo kainas.\n\nDabartinė jūsų teritorija: <b>{esamas_miestas}</b>.\nPasirinkite miestą arba visą Lietuvą:",
                "parse_mode": "HTML",
                "reply_markup": miestu_klaviatura()
            })
        else:
            miestas = gauti_vartotojo_miesta(chat_id)
            zinute = suformuoti_zinute(miestas)
            siusti_tg("sendMessage", {
                "chat_id": chat_id,
                "text": zinute,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": keisti_miesta_mygtukas()
            })

    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        cb_id = cb["id"]
        data = cb.get("data", "")

        siusti_tg("answerCallbackQuery", {"callback_query_id": cb_id})

        if data == "choose_city":
            siusti_tg("sendMessage", {
                "chat_id": chat_id,
                "text": "📍 Pasirinkite, kurios teritorijos mažiausias kainas norite matyti šiandien ir gauti kas rytą:",
                "reply_markup": miestu_klaviatura()
            })
        elif data.startswith("city:"):
            pasirinktas_miestas = data.split(":", 1)[1]
            issaugoti_vartotojo_miesta(chat_id, pasirinktas_miestas)
            zinute = suformuoti_zinute(pasirinktas_miestas)
            siusti_tg("sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ Išsaugota teritorija: <b>{pasirinktas_miestas}</b> (kito ryto suvestinė bus iš šios vietovės).\n\n{zinute}",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": keisti_miesta_mygtukas()
            })

    return jsonify({"ok": True})
