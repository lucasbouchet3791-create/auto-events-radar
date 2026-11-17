import json
import datetime

# Ici, ton futur script ira scraper les sites (FFSA, LVA, etc.) 
# Pour l'instant, il structure les données propres pour ton application.
events = [
    {
        "id": 1,
        "title": "Rallye d'Automne La Rochelle",
        "category": "rallye",
        "date": "2026-11-21",
        "city": "Châtelaillon-Plage (17)",
        "lat": 46.0744,
        "lng": -1.0886,
        "description": "Épreuve officielle mise à jour automatiquement par le script Python.",
        "url": "https://www.ffsa.org",
        "stages": [
            { "name": "ES 1 - Les Marais", "km": "14.2 km", "time": "09h15", "spectator": "Épingle de Ballon", "start": [46.058, -0.955], "end": [46.012, -0.910] }
        ]
    }
]

# Écriture dans le fichier events.json lu par ton site
with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=4)

print("Fichier events.json mis à jour avec succès !")
