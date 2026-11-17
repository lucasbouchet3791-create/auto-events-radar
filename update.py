import json
import os
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

def fetch_public_events():
    """Interroge l'API publique OpenDataSoft (100% ouverte sans clé) pour les événements auto en France."""
    events = []
    seen_titles = set()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Requête sur le jeu de données public des événements OpenAgenda hébergé sur OpenDataSoft
    keywords = ["rallye", "automobile", "voitures anciennes", "rassemblement", "circuit", "slalom", "course de cote"]
    
    for kw in keywords:
        url = f"https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records?where=search(title_fr%2C%20%22{kw}%22)%20AND%20firstdate_begin%20%3E%3D%20%22{today}%22&limit=40"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            data = res.json()
            for item in data.get("results", []):
                title = item.get("title_fr")
                if not title or title in seen_titles:
                    continue
                
                # Filtrage pour éviter les hors-sujets (ex: "rallye lecture")
                full_text = (title + " " + (item.get("description_fr") or "")).lower()
                if not any(word in full_text for word in ["voiture", "auto", "moto", "pilote", "circuit", "ffsa", "véhicule", "mécanique", "youngtimer", "ancienne", "rallye"]):
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

                # Catégorisation
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
                desc = item.get("description_fr") or "Événement automobile recensé automatiquement."

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
                    "url": item.get("canonicalurl") or "https://www.ffsa.org",
                    "stages": []
                })
        except Exception as e:
            print(f"Erreur sur {kw} : {e}")

    return events

print("Collecte des événements en cours...")
collected = fetch_public_events()

# Toujours inclure les grands rendez-vous de référence (avec spéciales détaillées)
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

final_events = reference_events + collected

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(final_events, f, ensure_ascii=False, indent=4)

print(f"Succès : {len(final_events)} événements enregistrés dans events.json !")
