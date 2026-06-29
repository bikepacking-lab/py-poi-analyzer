#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test
"""

from pathlib import Path
import logging
import gpxpy
import gpxpy.gpx

from analyzers.track_analyzer import TrackAnalyzer
from config import BASE_DIR

logging.basicConfig(level=logging.INFO)

def create_test_gpx(file_path: Path):
    """Crée un GPX de test"""
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    
    points = [
        (48.8566, 2.3522),
        (48.8600, 2.3700),
        (48.8500, 2.3800),
        (48.8400, 2.3500),
        (48.8450, 2.3300),
        (48.8566, 2.3522),
    ]
    
    for lat, lon in points:
        point = gpxpy.gpx.GPXTrackPoint(lat, lon)
        segment.points.append(point)
    
    with open(file_path, 'w') as f:
        f.write(gpx.to_xml())
    
    print(f"GPX créé: {file_path}")

def test():
    print("\n" + "="*60)
    print("TEST GPS TRACE ANALYZER")
    print("="*60 + "\n")
    
    test_dir = BASE_DIR / 'test_data'
    test_dir.mkdir(exist_ok=True)
    
    test_gpx = test_dir / 'test_track.gpx'
    if not test_gpx.exists():
        create_test_gpx(test_gpx)
    
    print("Lancement de l'analyse...")
    analyzer = TrackAnalyzer()
    
    try:
        results = analyzer.analyze(
            test_gpx,
            poi_types=['water', 'refueling', 'bivouac'],
            report_formats=['json', 'csv', 'pdf']
        )
        
        print("\n✅ TEST RÉUSSI!")
        print(f"ID: {results['analysis_id']}")
        print(f"POI: {results['num_pois']}")
        print(f"Dossier: {results['analysis_dir']}")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = test()
    sys.exit(0 if success else 1)