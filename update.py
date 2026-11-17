import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Cache de géocodage en mémoire pour éviter de refaire 2 fois la même requête ville
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
    """Charge les rallyes avec tracés détaillés dont la date n'est pas encore passée."""
    if not os.path.exists('rallyes_traces.json'):
        return []
    try:
        with open('rallyes_traces.json', 'r', encoding='utf-8') as f:
            traces = json.load(f)
        active_traces = [ev for ev in traces if ev.get("date", "") >= today_str]
        if len(active_traces) != len(traces):
            with open('rallyes_traces.json', 'w', encoding='utf-8') as f:
                json.dump(active_traces, f, ensure_ascii=False, indent=4)
        return active_traces
    except Exception as e:
        print(f"Erreur lecture rallyes_traces.json : {e}")
        return []

def fetch_opendatasoft_events(today_str, seen_titles):
    """Source 1 : Base publique OpenDataSoft élargie."""
    events = []
    keywords = [
        "voitures anciennes", "véhicules anciens", "rassemblement auto",
        "sport auto", "bourse auto", "rallye", "course de côte",
        "trackday", "youngtimers", "rétromobile", "cars and coffee",
        "véhicules de collection", "exposition auto", "slalom"
    ]

    must_have = [
        "voiture", "automobile", "véhicule", "youngtimer", "ancienne",
        "sportive", "rallye", "pilote", "circuit", "ffsa", "rétro",
        "mécanique", "collection", "gti", "porsche", "alpine", "ferrari"
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
            print(f"Erreur OpenDataSoft sur {kw} : {e}")

    return events

def fetch_newsdancienne_events(today_str, seen_titles):
    """Source 2 : Scraping de l'agenda spécialisé News d'Anciennes (rassos, bourses, rallyes historiques)."""
    events = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # On parcourt les 4 premières pages de l'agenda à venir
    for page in range(1, 5):
        url = f"https://newsdancienne.com/agenda/liste/?tribe-bar-date={today_str}&paged={page}"
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200:
                break
            
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('article')
            if not articles:
                break

            for art in articles:
                title_tag = art.find(['h2', 'h3'])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                if not title or title.lower() in seen_titles:
                    continue

                link_tag = title_tag.find('a')
                ev_url = link_tag['href'] if link_tag and link_tag.has_attr('href') else url

                # Extraction de la date (balise time)
                time_tag = art.find('time')
                date_str = time_tag['datetime'][:10] if time_tag and time_tag.has_attr('datetime') else today_str

                # Extraction du lieu / code postal dans le texte de l'article
                text_block = art.get_text(" ", strip=True)
                # Recherche d'un code postal français (5 chiffres) suivi du nom de la ville
                match_cp = re.search(r'\b(\d{5})\s+([A-ZÀ-Ÿa-zà-ÿ\-\'\s]{2,30})', text_block)
                if match_cp:
                    postal = match_cp.group(1)
                    city_raw = match_cp.group(2).split(',')[0].strip()
                    lat, lng = get_lat_lng(f"{postal} {city_raw}")
                    city_label = f"{city_raw} ({postal[:2]})"
                else:
                    continue

                if not lat or not lng:
                    continue

                t_lower = title.lower()
                if "rallye" in t_lower or "montée" in t_lower:
                    cat = "rallye"
                elif "circuit" in t_lower or "piste" in t_lower:
                    cat = "circuit"
                else:
                    cat = "rasso"

                seen_titles.add(title.lower())
                events.append({
                    "title": title,
                    "category": cat,
                    "date": date_str,
                    "city": city_label,
                    "lat": float(lat),
                    "lng": float(lng),
                    "description": "Événement recensé via l'agenda spécialisé News d'Anciennes.",
                    "url": ev_url,
                    "stages": []
                })
        except Exception as e:
            print(f"Erreur scraping page {page} : {e}")

    return events

today = datetime.now().strftime("%Y-%m-%d")
seen = set()

# 1. Rallyes avec tracés détaillés
active_rallies = load_active_rally_traces(today)
for r in active_rallies:
    seen.add(r["title"].lower())

# 2. Événements spécialisés (News d'Anciennes)
specialized_events = fetch_newsdancienne_events(today, seen)

# 3. Événements publics (OpenDataSoft)
public_events = fetch_opendatasoft_events(today, seen)

# Fusion et attribution d'ID propres
all_combined = active_rallies + specialized_events + public_events
for idx, ev in enumerate(all_combined, start=1):
    if "id" not in ev:
        ev["id"] = idx

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(all_combined, f, ensure_ascii=False, indent=4)

print(f"Bilan : {len(active_rallies)} tracés rallye + {len(specialized_events)} spécialisés + {len(public_events)} publics = {len(all_combined)} événements !")
