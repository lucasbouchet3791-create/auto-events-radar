import json
import os
import requests
from datetime import datetime

def get_lat_lng(city_name):
    try:
        url = f"https://api-adresse.data.gouv.fr/search/?q={requests.utils.quote(city_name)}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res.get('features'):
            coords = res['features'][0]['geometry']['coordinates']
            return coords[1], coords[0]
    except Exception:
        pass
    return None, None

def load_active_rally_traces(today_str):
    """Charge uniquement les rallyes avec tracés dont la date n'est pas encore passée."""
    if not os.path.exists('rallyes_traces.json'):
        return []
    
    try:
        with open('rallyes_traces.json', 'r', encoding='utf-8') as f:
            traces = json.load(f)
        
        # Filtrage : on ne garde que les rallyes du jour même ou à venir
        active_traces = [ev for ev in traces if ev.get("date", "") >= today_str]
        
        # On met à jour rallyes_traces.json pour purger définitivement les anciens tracés
        if len(active_traces) != len(traces):
            with open('rallyes_traces.json', 'w', encoding='utf-8') as f:
                json.dump(active_traces, f, ensure_ascii=False, indent=4)
                
        return active_traces
    except Exception as e:
        print(f"Erreur lecture rallyes_traces.json : {e}")
        return []

def fetch_clean_auto_events(today_str):
    events = []
    seen_titles = set()

    keywords = [
        "voitures anciennes", "véhicules anciens", "rassemblement auto",
        "sport auto", "bourse auto", "rallye automobile", "course de côte",
        "trackday", "youngtimers"
    ]

    must_have = [
        "voiture", "automobile", "véhicule", "youngtimer", "ancienne",
        "sportive", "rallye", "pilote", "circuit", "ffsa", "rétro", "mécanique"
    ]

    blacklist = [
        "entreprise", "entreprises", "industrie", "industriel", "uimm", "randstad",
        "intérim", "recrutement", "emploi", "métiers", "mission locale", "france travail",
        "étudiant", "iut", "lycée", "école", "stage", "alternance", "formation",
        "rando", "randonnée", "pédestre", "marche", "running", "trail", "vélo", "vtt",
        "célibataire", "bovine", "carcasse", "circuit court", "santé", "photo",
        "spectacle", "webinaire", "atelier", "afterwork", "benchmarking", "supply chain"
    ]

    for kw in keywords:
        url = f"https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records?where=search(title_fr%2C%20%22{requests.utils.quote(kw)}%22)%20AND%20firstdate_begin%20%3E%3D%20%22{today_str}%22&limit=30"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            data = res.json()

            for item in data.get("results", []):
                title = (item.get("title_fr") or "").strip()
                if not title or title in seen_titles:
                    continue

                desc = (item.get("description_fr") or "").strip()
                full_text = f"{title} {desc}".lower()

                if any(bad in full_text for bad in blacklist):
                    continue
                if not any(good in full_text for good in must_have):
                    continue

                coords = item.get("location_coordinates")
                city = item.get("location_city", "")
                postal = item.get("location_postalcode", "")

                if coords and "lat" in coords and "lon" in coords:
                    lat, lng = coords["lat"], coords["lon"]
                elif city:
                    lat, lng = get_lat_lng(f"{city} {postal}")
                else:
                    continue

                if not lat or not lng:
                    continue

                t_lower = title.lower()
                if "rallye" in t_lower:
                    cat = "rallye"
                elif "circuit" in t_lower or "trackday" in t_lower:
                    cat = "circuit"
                elif "côte" in t_lower or "cote" in t_lower or "slalom" in t_lower:
                    cat = "cote"
                else:
                    cat = "rasso"

                date_str = (item.get("firstdate_begin") or today_str)[:10]
                clean_desc = desc if desc else "Événement automobile recensé en France."

                seen_titles.add(title)
                events.append({
                    "id": len(events) + 1,
                    "title": title,
                    "category": cat,
                    "date": date_str,
                    "city": f"{city} ({postal[:2]})" if postal else city,
                    "lat": float(lat),
                    "lng": float(lng),
                    "description": clean_desc[:220] + "..." if len(clean_desc) > 220 else clean_desc,
                    "url": item.get("canonicalurl") or "https://www.ffsa.org",
                    "stages": []
                })
        except Exception as e:
            print(f"Erreur sur {kw} : {e}")

    return events

today = datetime.now().strftime("%Y-%m-%d")

# 1. Récupération des tracés actifs (et suppression automatique des passés)
active_rallies = load_active_rally_traces(today)

# 2. Récupération des événements généraux à venir
collected_events = fetch_clean_auto_events(today)

# 3. Fusion dans events.json
final_events = active_rallies + collected_events

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(final_events, f, ensure_ascii=False, indent=4)

print(f"Mise à jour terminée : {len(active_rallies)} rallyes avec tracés actifs et {len(collected_events)} événements à venir.")
