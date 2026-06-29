#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS Trace Analyzer
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from config import BASE_DIR
from analyzers.track_analyzer import TrackAnalyzer

# Configuration pour l'encodage UTF-8 sur Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Configuration du logging avec encodage UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(name)s:%(lineno)s - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'analyzer-{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Analyseur de traces GPS')
    parser.add_argument('file', type=Path, help='Fichier GPX a analyser')
    parser.add_argument('--poi-types', nargs='+', default=None, 
                       help='Types de POI (water, refueling, bivouac, accommodation, bike-repair, pharmacy)')
    parser.add_argument('--report-formats', nargs='+', default=None,
                       help='Formats de rapport (json, csv, xlsx, docx, pdf, pdf-map, gpx-enriched, kml-enriched, tcx-enriched, fit-data)')
    parser.add_argument('--debug', action='store_true', help='Mode debug')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.file.exists():
        logger.error(f"Fichier introuvable: {args.file}")
        sys.exit(1)
    
    analyzer = TrackAnalyzer()
    
    try:
        results = analyzer.analyze(
            args.file,
            poi_types=args.poi_types,
            report_formats=args.report_formats
        )
        
        print("\n" + "="*60)
        print("RESULTATS")
        print("="*60)
        print(f"ID: {results['analysis_id']}")
        print(f"Distance: {results['total_distance']:.2f} km")
        print(f"POI: {results['num_pois']}")
        print(f"Dossier: {results['analysis_dir']}")
        
        if results.get('reports'):
            print("\nRapports generes:")
            for fmt, path in results['reports'].items():
                print(f"  - {fmt}: {Path(path).name}")
        
        if results.get('summary'):
            print(f"""
📁 Fichier
───────────────────────────────────────────────────────────
Nom        : {results['summary']['file_info']['name']}
Taille     : {results['summary']['file_info']['size_mb']} Mo
Extension  : {results['summary']['file_info']['extension']}

🚴 Trace
───────────────────────────────────────────────────────────
Distance   : {results['summary']['track_info']['total_distance_km']:.2f} km
Points     : {results['summary']['track_info']['total_points']}
Altitude   : {'Oui' if results['summary']['track_info']['has_elevation'] else 'Non'}
Horodatage : {'Oui' if results['summary']['track_info']['has_time'] else 'Non'}

✂️  Découpage
───────────────────────────────────────────────────────────
Activé     : {results['summary']['split_info']['enabled']}
Max segment: {results['summary']['split_info']['max_distance_km']} km

🔍 Recherche POI
───────────────────────────────────────────────────────────
BBoxes           : {results['summary']['poi_search']['bboxes_count']}
Durée recherche  : {results['summary']['poi_search']['duration_seconds']:.2f} s
Calcul distances : {results['summary']['poi_search']['distance_calculation_seconds']:.2f} s

POI trouvés
───────────────────────────────────────────────────────────
Total      : {results['summary']['poi_search']['results']['total_found']}
Par type   : {results['summary']['poi_search']['results']['by_type']}
OSM types  : {results['summary']['poi_search']['results']['by_osm_type']}
Nommés     : {results['summary']['poi_search']['results']['named_count']}
Sans nom   : {results['summary']['poi_search']['results']['unnamed_count']}

Distances
───────────────────────────────────────────────────────────
Min        : {results['summary']['poi_search']['distances']['min_km']:.3f} km
Moyenne    : {results['summary']['poi_search']['distances']['avg_km']:.3f} km
Max        : {results['summary']['poi_search']['distances']['max_km']:.3f} km

⚡ Performances
───────────────────────────────────────────────────────────
Total      : {results['summary']['performance']['total_duration_seconds']:.2f} s
Recherche  : {results['summary']['performance']['search_duration_seconds']:.2f} s
Rapport    : {results['summary']['performance']['report_generation_seconds']:.2f} s

ℹ️ Recommandations & Conseils
───────────────────────────────────────────────────────────
- {"\n- ".join(results['summary']['recommendations'])}
""")
                
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Erreur: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()