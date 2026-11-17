import json
import os
import requests
from datetime import datetime

GEO_CACHE = {}

def get_lat_lng(city_query):
    """Récupère les coordonnées GPS exactes via l'API du gouvernement français."""
    if not city_query:
        return None, None
    clean_q = city_query.strip()
    if clean_q in GEO_CACHE:
        return GEO_CACHE[clean_q]

    try:
        url = f"https://api-adresse.data.gouv.fr/search/?q={requests.utils.quote(clean_q)}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res.get('features'):
            coords = res['features'][0]['geometry']['coordinates']
            GEO_CACHE[clean_q] = (coords[1], coords[0])
            return coords[1], coords[0]
    except Exception:
        pass
    
    GEO_CACHE[clean_q] = (None, None)
    return None, None

def load_active_rally_traces(today_str):
    """Charge les rallyes avec tracés détaillés dont la date n'est pas passée."""
    if not os.path.exists('rallyes_traces.json'):
        return []
    try:
        with open('rallyes_traces.json', 'r', encoding='utf-8') as f:
            traces = json.load(f)
        active_traces = [ev for ev in traces if ev.get("date", "") >= today_str]
        return active_traces
    except Exception as e:
        print(f"Erreur lecture rallyes_traces.json : {e}")
        return []

def fetch_opendatasoft_events(today_str, seen_titles):
    """Récupère un large volume d'événements automobiles et de collection en France."""
    events = []
    
    # Mots-clés larges mais ciblés pour maximiser les résultats
    keywords = [
        "voiture", "automobile", "véhicule ancien", "rassemblement", "bourse auto", 
        "rallye", "course de côte", "trackday", "youngtimers", "rétro", 
        "collection", "moto ancienne", "salon auto", "concentration"
    ]

    # Mots-clés pour valider l'univers mécanique/auto
    must_have = [
        "voiture", "automobile", "véhicule", "youngtimer", "ancienne",
        "sportive", "rallye", "pilote", "circuit", "ffsa", "rétro",
        "mécanique", "collection", "gti", "porsche", "alpine", "ferrari",
        "salon", "bourse", "rassemblement", "concentration", "expo"
    ]

    # Exclusion stricte des faux positifs (intérim, emploi, rando pédestre, etc.)
    blacklist = [
        "entreprise", "industrie", "uimm", "randstad", "intérim", "recrutement", 
        "emploi", "métiers", "mission locale", "france travail", "étudiant", "iut", 
        "lycée", "école", "stage", "alternance", "formation", "rando", "randonnée", 
        "pédestre", "marche", "running", "trail", "vélo", "vtt", "célibataire", 
        "bovine", "carcasse", "circuit court", "santé", "webinaire", "atelier", "afterwork"
    ]

    for kw in keywords:
        url = f"https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records?where=search(title_fr%2C%20%22{requests.utils.quote(kw)}%22)%20AND%20firstdate_begin%20%3E%3D%20%22{today_str}%22&limit=100"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            data = res.json()

            for item in data.get("results", []):
                title = (item.get("title_fr") or "").strip()
                if not title or title.lower() in seen_titles:
                    continue

                desc = (item.get("description_fr") or "").strip()
                full_text = f"{title} {desc}".lower()

                # Si un mot interdit est présent, on ignore
                if any(bad in full_text for bad in blacklist):
                    continue
                # Si aucun mot automobile n'est présent, on ignore
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

                seen_titles.add(title.lower())
                events.append({
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
seen = set()

# 1. Rallyes avec tracés détaillés
active_rallies = load_active_rally_traces(today)
for r in active_rallies:
    seen.add(r["title"].lower())

# 2. Récupération large via l'API publique
public_events = fetch_opendatasoft_events(today, seen)

# Fusion
all_combined = active_rallies + public_events
for idx, ev in enumerate(all_combined, start=1):
    ev["id"] = idx

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(all_combined, f, ensure_ascii=False, indent=4)

print(f"Bilan : {len(active_rallies)} tracés rallye + {len(public_events)} événements publics = {len(all_combined)} événements au total !")
