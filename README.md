# Documentation GPS Trace Analyzer

## Table des matières

1. [Introduction](#introduction)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Utilisation](#utilisation)
6. [Formats supportés](#formats-supportés)
7. [API](#api)
8. [Développement](#développement)
9. [Dépannage](#dépannage)

---

## Introduction

GPS Trace Analyzer est un outil modulaire d'analyse de traces GPS permettant :

- La détection de Points d'Intérêt (POI) via Overpass API
- La génération de rapports multi-formats
- L'enrichissement de fichiers GPS
- La gestion de traces volumineuses avec split automatique
- Calcule estimation du temps d'activité par jour.
- La génération automatique d'un JSON récapitulant les étapes journalières et leurs POI.

Les formats acceptés en entrée d'analyse : GPX, TCX, FIT, KML.

Génération des raports d'analyse (PDF, DOCX, PDF + MAP/POI, etc.).

Conversion vers tous les formats en entrée.

Génération des formats enrichis des POI trouvés par l'analyse.

## Architecture

### Design Patterns utilisés

1. **Strategy Pattern** : Pour les générateurs (BaseGenerator)
2. **Singleton** : Pour le CacheManager
3. **Factory Pattern** : Pour les générateurs (GeneratorRegistry)
4. **Circuit Breaker** : Pour la gestion des erreurs
5. **Decorator Pattern** : Pour les retries et le cache

### Structure du projet

```text

gps_analyzer/
├── core/ # Fonctionnalités cœur
│ ├── gpx_processor.py 	# Traitement GPX
│ ├── poi_detector.py 	# Détection POI
│ ├── cache_manager.py 	# Gestion du cache
│ ├── file_converter.py # Conversion formats
│ └── time_estimator.py # Estimation du temps
├── analyzers/ # Analyseurs
│ ├── file_manager.py
│ ├── recommendation_manager.py
│ ├── stats_manager.py
│ ├── split_manager.py
│ └── track_analyzer.py # Analyseur principal
├── generators/ # Générateurs (Strategy Pattern)
│ ├── base_generator.py # Classe de base
│ ├── converters/ 	# Convertisseurs
│ │ ├── fit_converter.py
│ │ ├── kml_converter.py
│ │ ├── gpx_converter.py
│ │ └── tcx_converter.py
│ ├── reporters/ 	# Rapports
│ │ ├── csv_generator.py
│ │ ├── excel_generator.py
│ │ ├── json_generator.py
│ │ ├── pdf_generator.py
│ │ ├── pdf_map_generator.py
│ │ ├── word_generator.py
│ │ ├── word_map_generator.py
│ │ ├── gdocs_map_generator.py
│ │ └── gdoc_generator.py
│ └── enriched/ 	# Fichiers enrichis
│   ├── fit_generator.py
│   ├── gpx_generator.py
│   ├── tcx_generator.py
│   └── kml_generator.py
├── managers/ # Gestionnaires
│ └── gpx_manager.py # Gestion des GPX
├── utils/ # Utilitaires
│ ├── retry_manager.py 	# Retry intelligent
│ ├── validators.py # Validation
│ └── helpers.py # Fonctions aide
└── config.py # Configuration
```

## Installation

### Prérequis

- Python 3.8+
- Redis (optionnel, mais recommandé pour le cache)
- Pip

### Installation des dépendances

```text
# Installation des dépendances principales
pip install -r requirements.txt
```

## Utilisation

**Ligne de commande**

```bash
# Analyse basique
python main.py path/to/track.gpx

# Avec options
python main.py path/to/track.gpx \
    --poi-types water refueling bivouac \
    --report-formats json csv pdf \
    --debug

# Avec paramètres avancés
python main.py track.gpx \
    --radii '{"water":1000,"refueling":1500}' \
    --intervals '{"water":30,"refueling":40}' \
    --debug
```

Chaque analyse crée automatiquement dans son dossier de rapport un fichier
`analysis_report_<id>_summary.json` ainsi qu'un fichier
`analysis_report_<id>_stages.json`. Ce dernier répartit la trace en étapes
journalières selon la durée de journée configurée pour l'activité et contient,
pour chacune, les lieux de départ et d'arrivée obtenus par géocodage inverse
Nominatim/OpenStreetMap, la distance, le dénivelé positif, la durée estimée,
la vitesse moyenne estimée et les POI situés sur l'étape. Les coordonnées des
points de départ et d'arrivée sont envoyées à Nominatim; l'attribution
OpenStreetMap est incluse dans le JSON. Le chemin du fichier est aussi renvoyé
dans `results['stages_file']` lors d'une utilisation comme module.

**En tant que module**

```python
from analyzers.track_analyzer import TrackAnalyzer

# Création de l'analyseur
analyzer = TrackAnalyzer()

# Analyse
results = analyzer.analyze(
    input_file=Path('track.gpx'),
    poi_types=['water', 'refueling'],
    report_formats=['json', 'csv', 'pdf'],
    radii={
        'water': 1000,
        'refueling': 1500
    }
)

print(f"Analyse ID: {results['analysis_id']}")
print(f"POI trouvés: {results['num_pois']}")
```

```python
from pathlib import Path
from analyzers.track_analyzer import TrackAnalyzer
from core.cache_manager import get_cache_manager

# Avec cache personnalisé
cache = get_cache_manager()
analyzer = TrackAnalyzer()

# Configuration avancée
results = analyzer.analyze(
    input_file=Path('track.gpx'),
    poi_types=['water', 'refueling', 'bivouac', 'accommodation'],
    radii={
        'water': 800,
        'refueling': 1000,
        'bivouac': 1500,
        'accommodation': 2000
    },
    intervals={
        'water': 20,
        'refueling': 30,
        'bivouac': 50,
        'accommodation': 50
    },
    report_formats=['json', 'csv', 'xlsx', 'docx', 'pdf', 'pdf-map']
)

## Développement

**Ajout d'un nouveau générateur**

Créer une nouvelle classe héritant de BaseGenerator:

```python
from generators.base_generator import BaseGenerator

class MyCustomGenerator(BaseGenerator):
    def get_format_type(self) -> str:
        return 'my-format'
  
    def generate(self, data, output_dir, **kwargs):
        # Implémentation
        output_file = output_dir / f'output.myformat'
        # ... génération ...
        return output_file
Enregistrer le générateur:

python
from generators.base_generator import GeneratorRegistry

GeneratorRegistry.register('my-format', MyCustomGenerator)
Ajout d'un nouveau type de POI
Ajouter dans config.py:

python
AVAILABLE_POI_TYPES.append({
    "type": "new-poi",
    "label": "Nouveau POI",
    "icon": "🔵"
})

DEFAULT_POI_TAGS_OSM["new-poi"] = [
    '["tag"="value"]',
    '["other_tag"="other_value"]'
]
Ajouter les tags de recherche:

python
AVAILABLE_POI_TAGS_OSM["new-poi"] = [
    '["amenity"="new_poi"]',
    '["shop"="new_poi"]'
]
```

## Report Google Docs

**Ajouter le fichier credentials.json**

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Creer un projet
3. Activer Google Docs API et Google Drive API
4. Creer des credentials (Application de bureau)
5. Telecharger le JSON
6. Le placer dans `credentials/credentials.json`

**Lors du premier lancement avec `gdocs`:**

1. Une page web s'ouvrira
2. Connectez-vous avec votre compte Google
3. Acceptez les permissions
4. Le token est sauvegarde dans `credentials/token_gdocs.json`

## Liste des rapports disponibles

### Rapports d'analyse

* Format JSON Summary Data (Résumé des données)
* Format CSV (délémiteur standard : virgule)
* Format Excel
* Format Word
* Format Word avec Carte et POI
* Format PDF
* Format PDF avec Carte et POI
* Format Google Docs
* Format Google Docs avec Carte et POI

### Formats enrichis

* GPX Enrichis des POI
* KML Enrichis des POI
* TCX Enrichis des POI
* FIT Enrichis des POI (Format JSON + Outil Conversion Format FIT : [www.vertopal.com/en/convert/json-to-fit](https://www.vertopal.com/en/convert/json-to-fit))

## Conversions

* Format GPX
* Format KML
* Format TCX
* Format FIT (Format JSON + Outil Conversion Format FIT : [www.vertopal.com/en/convert/json-to-fit](https://www.vertopal.com/en/convert/json-to-fit))

## Liste des activités

Permet de calculer une estimation du temps nécessaire pour réaliser la trace selon l'activité.

Possibilité de personnaliser à ses propres besoins et conditions personnelles

```Python
# Configuration des types de pratique disponibles pour l'analyse de vitesse et de temps
# Vitesses moyennes par type de pratique (km/h)
# Note: Ces valeurs sont des estimations et peuvent varier selon le terrain, la condition physique, la météo, etc.
# N'hésitez pas à ajuster ces valeurs selon vos besoins et votre expérience personnelle.
DEFAULT_SPEEDS = {
    'cycling': 20.0,
    'mtb': 12.0, 
    'gravel': 16.0,
    'hiking': 4.5, 
    'running': 8.0, 
    'walking': 3.5,
    'default': 15.0 
}

# Durée de la journée par type de pratique (heures par jour)
DEFAULT_DAY_DURATION_HOURS = {
    'cycling': 8.0,
    'mtb': 8.0,
    'gravel': 8.0,
    'hiking': 8.0,
    'running': 8.0,
    'walking': 8.0,
    'default': 8.0
}
```

## Support

* Pour toute question ou problème : support@bikepacking-analyzer.com
* Contacter l'équipe de développement : lab@bikepacking-analyzer.com
* Ouvrir une issue sur GitHub : [github.com/bikepacking-lab/py-poi-analyzer](https://github.com/bikepacking-lab/py-poi-analyzer)

## Licence

> Ce projet est sous licence **Apache License 2.0** Voir le fichier **LICENSE** pour plus de détails.

## Contribution

Les contributions sont les bienvenues ! Veuillez suivre les guidelines de contribution.

Forker le projet

Créer une branche pour votre fonctionnalité

Commiter vos changements

Pousser vers la branche

Créer une Pull Request

## Remerciements

Outil de conversion en ligne JSON Data vers Format FIT :[ github.com/dapperdal/technogym_json_to_fit](https://github.com/dapperdal/technogym_json_to_fit)

Librairie de convertion JSON Data vers Format Fit [github.com/dapperdal/technogym_json_to_fit](https://github.com/dapperdal/technogym_json_to_fit)

Overpass API Recherche POI : [openstreetmap.org](https://openstreetmap.org/)

## Résumé des améliorations

- Architecture évolutive : Pattern Strategy pour les générateurs, facilitant l'ajout de nouveaux formats
- Gestion des erreurs robuste : RetryManager avec backoff exponentiel, jitter et Circuit Breaker
- Support FIT : Génération de données FIT (au format JSON pour l'instant, prêt pour fitdecode)
- Documentation complète : Markdown détaillé avec sections pour les utilisateurs et les développeurs
- Extensibilité : Facile d'ajouter de nouveaux POI, formats, ou fonctionnalités

## Corrections en priorité

* Conversion JSON Data vers FIT Binary
