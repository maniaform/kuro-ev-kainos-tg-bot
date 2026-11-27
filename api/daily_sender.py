import os
import requests
from prices_engine import gauti_visus_duomenis, suformuoti_zinute, keisti_miesta_mygtukas

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
TG_API = "https://telegram.org" + "/bot" + BOT_TOKEN

def gauti_visus_vartotojus():
    r = requests.post(
        REDIS_URL,
        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        json=["HGETALL", "ev_fuel_users"],
        timeout=15
    )
    res = r.json().get("result") or []
    vartotojai = {}
    for i in range(0, len(res), 2):
        vartotojai[res[i]] = res[i + 1]
    return vartotojai

def paleisti_rytini_siuntima():
    vartotojai = gauti_visus_vartotojus()
    if not vartotojai:
        print("Prenumeratorių kol kas nėra.")
        return

    fuel_data, ev_data = gauti_visus_duomenis()
    kesas_pagal_miesta = {}

    for chat_id, miestas in vartotojai.items():
        if miestas not in kesas_pagal_miesta:
            kesas_pagal_miesta[miestas] = suformuoti_zinute(miestas, fuel_data, ev_data)

        try:
            requests.post(f"{TG_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": kesas_pagal_miesta[miestas],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": keisti_miesta_mygtukas()
            }, timeout=10)
            print(f"Išsiųsta vartotojui {chat_id} ({miestas})")
        except Exception as e:
            print(f"Klaida siunčiant {chat_id}:", e)

if __name__ == "__main__":
    paleisti_rytini_siuntima()
