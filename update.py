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

def fetch_clean_auto_events():
    """Récupère uniquement les vrais événements automobiles en France."""
    events = []
    seen_titles = set()
    today = datetime.now().strftime("%Y-%m-%d")

    # Mots-clés ciblés
    keywords = [
        "voitures anciennes",
        "véhicules anciens",
        "rassemblement auto",
        "sport auto",
        "bourse auto",
        "rallye automobile",
        "course de côte",
        "trackday"
    ]

    # Mots-clés obligatoires pour valider qu'il s'agit bien d'automobile/sport mécanique
    must_have = [
        "voiture", "automobile", "véhicule", "youngtimer", "ancienne",
        "sportive", "rallye", "pilote", "circuit", "ffsa", "auto", "rétro"
    ]

    # Mots-clés d'exclusion (pour bloquer les randos pédestres, l'emploi et l'agriculture)
    blacklist = [
        "rando", "randonnée", "pédestre", "marche", "célibataire",
        "industrie", "entreprise", "intérim", "randstad", "recrutement",
        "emploi", "métiers", "bovine", "carcasse", "circuit court",
        "santé", "photo", "spectacle", "webinaire", "atelier", "formation"
    ]

    for kw in keywords:
        url = f"https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records?where=search(title_fr%2C%20%22{requests.utils.quote(kw)}%22)%20AND%20firstdate_begin%20%3E%3D%20%22{today}%22&limit=30"
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

                # 1. Rejeter si un mot interdit est présent
                if any(bad in full_text for bad in blacklist):
                    continue

                # 2. Exiger au moins un mot-clé automobile
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

                # Catégorisation propre
                t_lower = title.lower()
                if "rallye" in t_lower:
                    cat = "rallye"
                elif "circuit" in t_lower or "trackday" in t_lower:
                    cat = "circuit"
                elif "côte" in t_lower or "cote" in t_lower or "slalom" in t_lower:
                    cat = "cote"
                else:
                    cat = "rasso"

                date_str = (item.get("firstdate_begin") or today)[:10]
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

# Événements majeurs de référence (toujours présents, avec spéciales détaillées)
reference_events = [
    {
        "id": 9001,
        "title": "Rallye d'Automne La Rochelle",
        "category": "rallye",
        "date": "2026-11-21",
        "city": "Châtelaillon-Plage (17)",
        "lat": 46.0744,
        "lng": -1.0886,
        "description": "Épreuve mythique de la Coupe de France des Rallyes (Coeff. 4). Parc d'assistance sur le front de mer.",
        "url": "https://www.ffsa.org",
        "stages": [
            { "name": "ES 1 / 4 - Les Marais", "km": "14.2 km", "time": "09h15 / 14h30", "spectator": "Épingle de Ballon (Accès D112)", "start": [46.058, -0.955], "end": [46.012, -0.910] },
            { "name": "ES 2 / 5 - La Devise", "km": "18.6 km", "time": "10h05 / 15h20", "spectator": "Bourg de Vandré - Chicane", "start": [46.055, -0.765], "end": [45.980, -0.740] },
            { "name": "ES 3 / 6 - Aunis", "km": "11.8 km", "time": "11h00 / 16h15", "spectator": "Arrivée Surgères", "start": [46.105, -0.752], "end": [46.140, -0.820] }
        ]
    },
    {
        "id": 9002,
        "title": "Rassemblement Mensuel Véhicules Anciens & Prestige",
        "category": "rasso",
        "date": "2026-11-22",
        "city": "Rochefort (17)",
        "lat": 45.9367,
        "lng": -0.9617,
        "description": "Rendez-vous convivial sur le parking de la Corderie Royale. Ouvert aux youngtimers, sportives et anciennes.",
        "url": "https://www.lva-auto.fr",
        "stages": []
    },
    {
        "id": 9003,
        "title": "Journée Open Trackday - Circuit du Val de Vienne",
        "category": "circuit",
        "date": "2026-11-28",
        "city": "Le Vigeant (86)",
        "lat": 46.1972,
        "lng": 0.6358,
        "description": "Roulage libre par sessions (Berlines, GT, Monoplaces). Accès spectateurs gratuit dans les paddocks.",
        "url": "https://www.circuitvaldevienne.com",
        "stages": []
    },
    {
        "id": 9004,
        "title": "Rallye du Var - Finale Championnat de France",
        "category": "rallye",
        "date": "2026-11-27",
        "city": "Sainte-Maxime (83)",
        "lat": 43.3089,
        "lng": 6.6378,
        "description": "Finale du Championnat de France des Rallyes Asphalte sur les routes du massif des Maures.",
        "url": "https://www.ffsa.org",
        "stages": [
            { "name": "ES 1 - Col du Babaou", "km": "24.1 km", "time": "08h30", "spectator": "Sommet du Col", "start": [43.285, 6.455], "end": [43.310, 6.480] },
            { "name": "ES 2 - Collobrières", "km": "32.4 km", "time": "10h15", "spectator": "Épingle de la Chartreuse", "start": [43.235, 6.310], "end": [43.260, 6.380] }
        ]
    }
]

collected = fetch_clean_auto_events()
final_events = reference_events + collected

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(final_events, f, ensure_ascii=False, indent=4)

print(f"Terminé : {len(final_events)} vrais événements enregistrés !")
