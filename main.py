#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS Trace Analyzer
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from config import LOG_DIR
from analyzers.track_analyzer import TrackAnalyzer

# Configuration pour l'encodage UTF-8 sur Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
else:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    

# Configuration du logging avec encodage UTF-8

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(name)s:%(lineno)s - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'analyzer-{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
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
    parser.add_argument('--activity', type=str, default='gravel', choices=['cycling', 'mtb', 'gravel', 'hiking', 'running', 'walking'],
                       help='Type d\'activite (cycling, mtb, gravel, hiking, running, walking)')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.file.exists():
        logger.error(f"Fichier introuvable: {args.file}")
        sys.exit(1)
    
    analyzer = TrackAnalyzer()
    
    logger.info(f"Types POI: {args.poi_types}")
    logger.info(f"Formats: {args.report_formats}")
    logger.info(f"Activite: {args.activity}")
    try:
        results = analyzer.analyze(
            args.file,
            poi_types=args.poi_types,
            report_formats=args.report_formats,
            activity=args.activity
        )
        
        if results is None:
            logger.error("Aucun résultat généré.")
            sys.exit(1)
        
        print("\n" + "─"*60)
        print("RESULTATS")
        print("─"*60)
        print(f"{json.dumps(results, indent=2, ensure_ascii=False)}")
        print("─"*60 + "\n")

    except Exception as e:
        logger.error(f"Erreur: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()