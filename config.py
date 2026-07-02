#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / 'logs'
GPX_DIR = BASE_DIR / 'gpx'
REPORT_DIR = BASE_DIR / 'report'
CREDENTIALS_DIR = BASE_DIR / 'credentials'

# Création des répertoires
ALL_DIRS = [LOG_DIR, GPX_DIR, REPORT_DIR]
for d in ALL_DIRS:
    d.mkdir(parents=True, exist_ok=True)

# Configuration des limites
MAX_GPX_SIZE_MB = 5
MAX_GPX_DISTANCE_KM = 250.0
# CHUNK_DISTANCE_KM = 15.0
GPX_AUTO_SPLIT = True
# Configuration de l'élévation (dénivelé)
ELEVATION_MIN_VARIATION = 1.0
ELEVATION_SMOOTHING_WINDOW = 3
ELEVATION_SUBSAMPLE_STEP = 2
ELEVATION_SUBSAMPLE_THRESHOLD = 30000

# Configuration de l'analyse
ANALYSIS_MAX_PARALLEL = 2
ANALYSIS_TIMEOUT_SECONDS = 1200

# Configuration POI
POI_API_URL = 'https://overpass-api.de/api/interpreter'
POI_ENABLED = True
OVERPASS_DEBUG_MODE = True
MAX_TAGS_PER_TYPE = 20 # nombers filters per tag

# Configuration cache
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_TTL_SECONDS = 2
CACHE_REDIS_OPTIONS = {
    'protocol': 2,
    'decode_responses': False,
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True,
}

# Configuration des POI
DEFAULT_RADII = {
    "water": 800.0,
    "refueling": 800.0,
    "bivouac": 1000.0,
    "accommodation": 1000.0,
    "bike-repair": 5000.0,
    "pharmacy": 800.0
}

DEFAULT_INTERVALS = {
    "water": 20.0,
    "refueling": 40.0,
    "bivouac": 80.0,
    "accommodation": 80.0,
    "bike-repair": 80.0,
    "pharmacy": 40.0
}

DEFAULT_REPORT_FORMATS = ["json", "csv", "xlsx", "docx", "pdf", "pdf-map", "docx-map", "gdocs", "gdocs-map","fit-enriched","kml-enriched","tcx-enriched", "gpx-enriched", "tcx", "kml", "fit"]

AVAILABLE_REPORT_FORMATS = [
    {"type": "json", "label": "Format JSON Summary Data"},
    {"type": "csv", "label": "Report Format CSV"},
    {"type": "xlsx", "label": "Report Format EXCEL"},
    {"type": "docx", "label": "Format WORD"},
    {"type": "docx-map", "label": "Format WORD MAP+POI"},
    {"type": "gdocs", "label": "Format Google Docs"},
    {"type": "gdocs-map", "label": "Format Google Docs MAP+POI"},
    {"type": "pdf", "label": "Format PDF"},
    {"type": "pdf-map", "label": "Format PDF MAP+POI"},
    {"type": "gpx-enriched", "label": "Format GPX Enrichi POI"},
    {"type": "kml-enriched", "label": "Format KML Enrichi POI"},
    {"type": "tcx-enriched", "label": "Format TCX Enrichi POI"},
    {"type": "fit-enriched", "label": "Données FIT Enrichi POI (JSON Data + Outils conversion FIT)"},
    {"type": "gpx", "label": "Conversion au Format GPX"},
    {"type": "kml", "label": "Conversion au Format KML"},
    {"type": "tcx", "label": "Conversion au Format TCX"},
    {"type": "fit", "label": "Conversion au Format FIT (JSON Data + Outils conversion FIT)"}
]

DEFAULT_POI_TYPES = ["water", "refueling", "bivouac"]
AVAILABLE_POI_TYPES = [
    {"type": "water", "label": "Eau", "icon": "💧"},
    {"type": "refueling", "label": "Ravitaillement", "icon": "🥪"},
    {"type": "bivouac", "label": "Bivouac", "icon": "⛺"},
    {"type": "accommodation", "label": "Hébergement", "icon": "🏠"},
    {"type": "bike-repair", "label": "Réparation vélo", "icon": "🛠️"},
    {"type": "pharmacy", "label": "Pharmacie", "icon": "💊"}
]

DEFAULT_TYPE_GPX_SOURCE = ["gpx"]
AVAILABLE_TYPE_GPX_SOURCE = [
    {"type": "gpx", "label": "GPX source"},
    {"type": "kml", "label": "KML Source"},
    {"type": "tcx", "label": "TCX Source"},
    {"type": "fit", "label": "FIT Source"}
]

DEFAULT_POI_TAGS_OSM = {
    "water": [
        '["drinking_water"~"yes|treated"]',
        '["amenity"="drinking_water"]',
        '["man_made"="water_tap"]["drinking_water"!="no"]["access"!="private"]',
        '["natural"="spring"]["drinking_water"="yes"]',
        '["amenity"="fountain"]["drinking_water"="yes"]',
        '["man_made"="water_well"]["drinking_water"="yes"]["access"!="private"]',
        '["drinking_water"="yes"]["amenity"!="toilets"]["access"!="private"]'
    ],
    "refueling": [
        '["amenity"="vending_machine"]["vending"~"food|drinks|pizza|bread"]',
        '["shop"~"convenience|bakery|butcher|deli|greengrocer|farm|pastry"]',
        '["amenity"="fuel"]',
        '["amenity"~"fast_food|cafe"]',
        '["amenity"="restaurant"]["cuisine"~"burger|sandwich|kebab|pizza|tacos|fried_chicken"]'
    ],
    "bivouac": [
        '["tourism"="camp_site"]["access"!="private"]',
        '["tourism"="camp_site"]["camp_site"~"basic|backcountry"]',
        '["tourism"="wilderness_hut"]',
        '["building"="hut"]["access"!="private"]',
        '["amenity"="shelter"]["shelter_type"~"lean_to|basic_hut|weather_shelter"]',
        '["leisure"="firepit"]',
        '["tourism"="picnic_site"]["access"!="private"]',
        '["leisure"="picnic_table"]["access"!="private"]',
        '["camping"="yes"]["access"!="private"]',
        '["backcountry"="yes"]',
        '["boundary"="protected_area"]["protect_class"="6"]["camping"="yes"]',
        '["boundary"="national_park"]["camping"="yes"]'
        # '["tourism"="camp_site"]',
        # '["tourism"="wilderness_hut"]',
        # '["amenity"="shelter"]',
        # '["tourism"="camp_site"]["camp_site"~"basic|backcountry"]',
        # '["building"="hut"]["access"!="private"]',
        # '["amenity"="shelter"]["shelter_type"~"lean_to|basic_hut|weather_shelter"]',
        # '["leisure"="firepit"]',
        # '["tourism"="picnic_site"]["access"!="private"]',
        # '["leisure"="picnic_table"]["access"!="private"]',
        # '["camping"="yes"]["access"!="private"]',
        # '["backcountry"="yes"]',
        # '["boundary"="protected_area"]["protect_class"="6"]["camping"="yes"]',
        # '["boundary"="national_park"]["camping"="yes"]'
    ]
}

AVAILABLE_POI_TAGS_OSM = {
    "water": [
        '["drinking_water"~"yes|treated"]',
        '["amenity"="drinking_water"]',
        '["man_made"="water_tap"]["drinking_water"!="no"]["access"!="private"]',
        '["natural"="spring"]["drinking_water"="yes"]',
        '["amenity"="fountain"]["drinking_water"="yes"]',
        '["man_made"="water_well"]["drinking_water"="yes"]["access"!="private"]',
        '["drinking_water"="yes"]["amenity"!="toilets"]["access"!="private"]'
    ],
    "refueling": [
        '["amenity"="vending_machine"]["vending"~"food|drinks|pizza|bread"]',
        '["shop"~"convenience|bakery|butcher|deli|greengrocer|farm|pastry"]',
        '["amenity"="fuel"]',
        '["amenity"~"fast_food|cafe"]',
        '["amenity"="restaurant"]["cuisine"~"burger|sandwich|kebab|pizza|tacos|fried_chicken"]'
    ],
    "bivouac": [
        '["tourism"="camp_site"]["access"!="private"]',
        '["tourism"="camp_site"]["camp_site"~"basic|backcountry"]',
        '["tourism"="wilderness_hut"]',
        '["building"="hut"]["access"!="private"]',
        '["amenity"="shelter"]["shelter_type"~"lean_to|basic_hut|weather_shelter"]',
        '["leisure"="firepit"]',
        '["tourism"="picnic_site"]["access"!="private"]',
        '["leisure"="picnic_table"]["access"!="private"]',
        '["camping"="yes"]["access"!="private"]',
        '["backcountry"="yes"]',
        '["boundary"="protected_area"]["protect_class"="6"]["camping"="yes"]',
        '["boundary"="national_park"]["camping"="yes"]'
    ],
    "accommodation": [
        '["tourism"="hotel"]', '["tourism"="motel"]', '["tourism"="hostel"]',
        '["tourism"="guest_house"]', '["tourism"="bed_and_breakfast"]', '["tourism"="gite"]'
    ],
    "bike-repair": [
        '["shop"="bicycle"]', '["amenity"="bicycle_repair_station"]', 
        '["service:bicycle:repair"="yes"]'
    ],
    "pharmacy": [
        '["amenity"="pharmacy"]', '["healthcare"="pharmacy"]'
    ]
}