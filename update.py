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
    events = []
    seen_titles = set()
    today = datetime.now().strftime("%Y-%m-%d")

    keywords = [
        "voitures anciennes",
        "véhicules anciens",
        "rassemblement auto",
        "sport auto",
        "bourse auto",
        "rallye automobile",
        "course de côte",
        "trackday",
        "youngtimers"
    ]

    must_have = [
        "voiture", "automobile", "véhicule", "youngtimer", "ancienne",
        "sportive", "rallye", "pilote", "circuit", "ffsa", "rétro", "mécanique"
    ]

    # Liste d'exclusion renforcée (entreprises, écoles, emplois, sport pédestre, etc.)
    blacklist = [
        "entreprise", "entreprises", "industrie", "industriel", "uimm", "randstad",
        "intérim", "recrutement", "emploi", "métiers", "mission locale", "france travail",
        "étudiant", "iut", "lycée", "école", "stage", "alternance", "formation",
        "rando", "randonnée", "pédestre", "marche", "running", "trail", "vélo", "vtt",
        "célibataire", "bovine", "carcasse", "circuit court", "santé", "photo",
        "spectacle", "webinaire", "atelier", "afterwork", "benchmarking", "supply chain"
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

# Événements de référence avec tracés complets des spéciales et coordonnées des zones spectateurs
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
            {
                "name": "ES 1 / 4 - Les Marais",
                "km": "14.2 km",
                "time": "09h15 / 14h30",
                "path": [[46.058, -0.955], [46.042, -0.938], [46.028, -0.925], [46.012, -0.910]],
                "spectator_zones": [
                    { "name": "Zone Public 1 : Épingle de Ballon (Accès D112)", "coords": [46.042, -0.938] },
                    { "name": "Zone Public 2 : Saut du Canal", "coords": [46.028, -0.925] }
                ]
            },
            {
                "name": "ES 2 / 5 - La Devise",
                "km": "18.6 km",
                "time": "10h05 / 15h20",
                "path": [[46.055, -0.765], [46.025, -0.758], [45.998, -0.745], [45.980, -0.740]],
                "spectator_zones": [
                    { "name": "Zone Public : Chicane Bourg de Vandré", "coords": [46.025, -0.758] }
                ]
            },
            {
                "name": "ES 3 / 6 - Aunis",
                "km": "11.8 km",
                "time": "11h00 / 16h15",
                "path": [[46.105, -0.752], [46.122, -0.785], [46.140, -0.820]],
                "spectator_zones": [
                    { "name": "Zone Public : Épingle Arrivée Surgères", "coords": [46.122, -0.785] }
                ]
            }
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
            {
                "name": "ES 1 - Col du Babaou",
                "km": "24.1 km",
                "time": "08h30",
                "path": [[43.285, 6.455], [43.298, 6.468], [43.310, 6.480]],
                "spectator_zones": [
                    { "name": "Zone Public : Sommet du Col du Babaou", "coords": [43.298, 6.468] }
                ]
            },
            {
                "name": "ES 2 - Collobrières",
                "km": "32.4 km",
                "time": "10h15",
                "path": [[43.235, 6.310], [43.248, 6.345], [43.260, 6.380]],
                "spectator_zones": [
                    { "name": "Zone Public : Épingle de la Chartreuse", "coords": [43.248, 6.345] }
                ]
            }
        ]
    }
]

collected = fetch_clean_auto_events()
final_events = reference_events + collected

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(final_events, f, ensure_ascii=False, indent=4)

print(f"Succès : {len(final_events)} événements propres enregistrés !")
