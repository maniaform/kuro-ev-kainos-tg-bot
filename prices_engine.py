import os
import requests

FUEL_JSON_URL = "https://" + "benzinas-lt" + ".vercel.app/prices.json"
EV_JSON_URL = "https://" + "ev-kainos-lt" + ".vercel.app/ev_prices.json"

MIESTAI = [
    "Visa Lietuva", "Vilnius", "Kaunas", "Klaipėda", "Šiauliai", "Panevėžys",
    "Alytus", "Marijampolė", "Mažeikiai", "Jonava", "Utena", "Kėdainiai"
]

def gauti_visus_duomenis():
    fuel_data = {}
    ev_data = {}
    try:
        r1 = requests.get(FUEL_JSON_URL, timeout=15)
        if r1.ok:
            fuel_data = r1.json()
    except Exception as e:
        print("Klaida skaitant kuro JSON:", e)

    try:
        r2 = requests.get(EV_JSON_URL, timeout=15)
        if r2.ok:
            ev_data = r2.json()
    except Exception as e:
        print("Klaida skaitant EV JSON:", e)

    return fuel_data, ev_data

def rasti_pigiausia_kura(fuel_data, fuel_key, miestas):
    geriausias = None
    for net in fuel_data.get("networks", []):
        for st in net.get("stations", []):
            if miestas != "Visa Lietuva" and miestas.lower() not in (st.get("city") or "").lower():
                continue
            kaina = st.get(fuel_key)
            if isinstance(kaina, (int, float)) and kaina > 0:
                if geriausias is None or kaina < geriausias["price"]:
                    geriausias = {
                        "price": kaina,
                        "network": net.get("name", ""),
                        "city": st.get("city", ""),
                        "address": st.get("address", ""),
                        "diff": net.get(f"diff_{fuel_key}", 0)
                    }
    return geriausias

def rasti_pigiausia_ev(ev_data, miestas):
    geriausias = None
    for net in ev_data.get("networks", []):
        for st in net.get("stations", []):
            if miestas != "Visa Lietuva" and miestas.lower() not in (st.get("city") or "").lower():
                continue
            if st.get("is_free") or st.get("price") == 0:
                continue
            kaina = st.get("price")
            if isinstance(kaina, (int, float)) and kaina > 0:
                if geriausias is None or kaina < geriausias["price"]:
                    geriausias = {
                        "price": kaina,
                        "network": net.get("name", ""),
                        "city": st.get("city", ""),
                        "address": st.get("address", ""),
                        "kw": st.get("power_kw", ""),
                        "type": "DC" if st.get("is_dc") else "AC",
                        "diff": net.get("diff_dc" if st.get("is_dc") else "diff_ac", 0)
                    }
    return geriausias

def suformuoti_zinute(miestas="Visa Lietuva", fuel_data=None, ev_data=None):
    if fuel_data is None or ev_data is None:
        fuel_data, ev_data = gauti_visus_duomenis()

    a95 = rasti_pigiausia_kura(fuel_data, "a95", miestas)
    dyz = rasti_pigiausia_kura(fuel_data, "diesel", miestas)
    lpg = rasti_pigiausia_kura(fuel_data, "lpg", miestas)
    ev = rasti_pigiausia_ev(ev_data, miestas)

    def eilute(ikona, pav, item, matas="€"):
        if not item:
            return f"{ikona} <b>{pav}:</b> duomenų šioje vietovėje nėra"
        vieta = f"{item['city']}, {item['address']}" if miestas == "Visa Lietuva" else item['address']
        papildoma = f" ({item['type']}, iki {item['kw']} kW)" if "kw" in item and item["kw"] else ""
        return f"{ikona} <b>{pav}:</b> <code>{item['price']:.2f} {matas}</code> — <b>{item['network']}</b>{papildoma}\n      📍 <i>{vieta}</i>"

    tekstas = [
        f"🇱🇹 <b>Mažiausios kainos šiandien ({miestas})</b>\n",
        eilute("⛽", "A95 benzinas", a95, "€/l"),
        eilute("🚛", "Dyzelinas", dyz, "€/l"),
        eilute("🔥", "Dujos (LPG)", lpg, "€/l"),
        eilute("⚡", "EV įkrovimas", ev, "€/kWh"),
    ]

    # Papildoma informacija apie kainų pokyčius tik pačioje pabaigoje
    pokyciai = []
    for pav, obj in [("A95", a95), ("Dyz.", dyz), ("LPG", lpg), ("EV", ev)]:
        if obj and isinstance(obj.get("diff"), (int, float)) and obj["diff"] != 0:
            zenklas = "+" if obj["diff"] > 0 else ""
            pokyciai.append(f"{pav} {zenklas}{obj['diff']:.2f} €")

    tekstas.append("\n────────────────────")
    if pokyciai:
        tekstas.append(f"📊 <i>Pokytis per parą: {', '.join(pokyciai)}</i>")
    else:
        tekstas.append("📊 <i>Pokytis per parą: kainos nepakito (0.00 €)</i>")

    tekstas.append("🌐 <a href='https://vercel.app'>Kuro kainos</a> • <a href='https://vercel.app'>EV kainos</a>")
    return "\n".join(tekstas)

def miestu_klaviatura():
    mygtukai = []
    eile = []
    for m in MIESTAI:
        eile.append({"text": f"📍 {m}", "callback_data": f"city:{m}"})
        if len(eile) == 2:
            mygtukai.append(eile)
            eile = []
    if eile:
        mygtukai.append(eile)
    return {"inline_keyboard": mygtukai}

def keisti_miesta_mygtukas():
    return {
        "inline_keyboard": [
            [{"text": "📍 Pasirinkti / keisti miestą arba teritoriją", "callback_data": "choose_city"}]
        ]
    }
