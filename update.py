import json
import requests
from datetime import datetime

def get_lat_lng(city_name):
    """Récupère les coordonnées GPS exactes via l'API du gouvernement français."""
    try:
        url = f"https://api-adresse.data.gouv.fr/search/?q={requests.utils.quote(city_name)}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res.get('features'):
            coords = res['features'][0]['geometry']['coordinates']
            return coords[1], coords[0]
    except Exception:
        pass
    return None, None

def fetch_openagenda_auto_events():
    """Récupère automatiquement les événements auto, rallyes et rassos publiés sur OpenAgenda en France."""
    events = []
    keywords = ["rallye", "automobile", "voitures anciennes", "rassemblement auto", "circuit", "slalom"]
    seen_titles = set()
    
    # Date du jour au format ISO pour ne récupérer que les événements à venir
    today = datetime.now().strftime("%Y-%m-%d")

    for kw in keywords:
        url = f"https://openagenda.com/agendas/events.json?search={kw}&timings[gte]={today}&limit=30"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue
            data = response.json()
            for item in data.get("events", []):
                title = item.get("title", {}).get("fr") or item.get("title", {}).get("en")
                if not title or title in seen_titles:
                    continue
                
                location = item.get("location", {})
                city = location.get("city", "")
                postal = location.get("postalCode", "")
                lat = location.get("latitude")
                lng = location.get("longitude")

                # Si l'événement n'a pas de GPS intégré, on le géocode via l'API gouvernementale
                if (not lat or not lng) and city:
                    lat, lng = get_lat_lng(f"{city} {postal}")
                
                if not lat or not lng:
                    continue

                # Catégorisation automatique selon les mots-clés du titre
                t_lower = title.lower()
                if "rallye" in t_lower:
                    cat = "rallye"
                elif "circuit" in t_lower or "trackday" in t_lower:
                    cat = "circuit"
                elif "côte" in t_lower or "slalom" in t_lower:
                    cat = "cote"
                else:
                    cat = "rasso"

                # Extraction de la date
                timings = item.get("timings", [])
                date_str = timings[0].get("begin", "")[:10] if timings else today

                desc = item.get("description", {}).get("fr") or "Événement automobile recensé automatiquement."
                
                seen_titles.add(title)
                events.append({
                    "id": len(events) + 1,
                    "title": title,
                    "category": cat,
                    "date": date_str,
                    "city": f"{city} ({postal[:2]})" if postal else city,
                    "lat": float(lat),
                    "lng": float(lng),
                    "description": desc[:200] + "..." if len(desc) > 200 else desc,
                    "url": item.get("canonicalUrl", "https://openagenda.com"),
                    "stages": []
                })
        except Exception as e:
            print(f"Erreur sur le mot-clé {kw}: {e}")

    return events

# Exécution de la collecte
print("Recherche des événements automobiles en France en cours...")
collected_events = fetch_openagenda_auto_events()

# Sauvegarde dans events.json
with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(collected_events, f, ensure_ascii=False, indent=4)

print(f"Terminé : {len(collected_events)} événements réels trouvés et enregistrés !")
