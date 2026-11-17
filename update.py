import json
import requests

def get_lat_lng(city_name):
    """Interroge l'API officielle française pour trouver les coordonnées GPS d'une ville."""
    try:
        url = f"https://api-adresse.data.gouv.fr/search/?q={requests.utils.quote(city_name)}&limit=1"
        res = requests.get(url).json()
        if res.get('features'):
            coords = res['features'][0]['geometry']['coordinates']
            return coords[1], coords[0] # Retourne (lat, lng)
    except Exception as e:
        print(f"Erreur géocodage pour {city_name}: {e}")
    return 46.6033, 1.8883 # Centre de la France par défaut si introuvable

# === BASE DE DONNÉES DES ÉVÉNEMENTS ===
# Ici, tu pourras ajouter tes fonctions de scraping (BeautifulSoup) pour remplir cette liste automatiquement.
# Pour l'instant, voici une structure prête à recevoir des événements de toute la France.
raw_events = [
    {
        "title": "Rallye du Var",
        "category": "rallye",
        "date": "2026-11-27",
        "city": "Sainte-Maxime (83)",
        "description": "Finale du championnat de France des rallyes.",
        "url": "https://www.ffsa.org",
        "stages": [
            { "name": "ES 1 - Col du Babaou", "km": "24.1 km", "time": "08h30", "spectator": "Zone public col", "start": [43.285, 6.455], "end": [43.310, 6.480] }
        ]
    },
    {
        "title": "Rasso Mensuel Youngtimers",
        "category": "rasso",
        "date": "2026-11-29",
        "city": "Bordeaux (33)",
        "description": "Rassemblement de sportives des années 80 à 2000.",
        "url": "https://www.newsdancienne.com",
        "stages": []
    }
]

events_list = []

for idx, ev in enumerate(raw_events, start=1):
    lat, lng = get_lat_lng(ev["city"])
    event_data = {
        "id": idx,
        "title": ev["title"],
        "category": ev["category"],
        "date": ev["date"],
        "city": ev["city"],
        "lat": lat,
        "lng": lng,
        "description": ev["description"],
        "url": ev["url"],
        "stages": ev.get("stages", [])
    }
    events_list.append(event_data)

# Enregistrement dans events.json lu par ton site
with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(events_list, f, ensure_ascii=False, indent=4)

print(f"{len(events_list)} événements géolocalisés et enregistrés avec succès dans events.json !")
