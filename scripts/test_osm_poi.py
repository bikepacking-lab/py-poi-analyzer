#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de la détection POI avec les tags OSM complexes
"""

import logging
from core.poi_detector import POIDetector
from core.cache_manager import get_cache_manager
from config import DEFAULT_POI_TAGS_OSM, DEFAULT_RADII, MAX_TAGS_PER_TYPE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_osm_tags():
    """Test de la détection avec les tags OSM"""
    
    print("\n" + "="*60)
    print("TEST DÉTECTION POI AVEC TAGS OSM")
    print("="*60 + "\n")
    
    # Initialisation
    cache = get_cache_manager()
    detector = POIDetector(cache)
    
    # BBox de test (Paris)
    bbox = (48.85, 2.35, 48.86, 2.36)
    
    # Types de POI à tester
    poi_types = ['water', 'refueling', 'bivouac']
    
    # Tags OSM complets
    tags_config = DEFAULT_POI_TAGS_OSM
    
    print("🔍 Configuration des tags OSM:")
    for poi_type in poi_types:
        if poi_type in tags_config:
            print(f"  • {poi_type}: {len(tags_config[poi_type])} filtres")
            for i, tag_filter in enumerate(tags_config[poi_type][:3], 1):
                print(f"    {i}. {tag_filter}")
            if len(tags_config[poi_type]) > 3:
                print(f"    ... et {len(tags_config[poi_type]) - 3} autres")
    
    print(f"\n📍 BBox de test: {bbox}")
    print(f"🏷️ Types: {poi_types}")
    print(f"📏 Rayon: {max(DEFAULT_RADII.values())}m")
    
    # Détection
    print("\n🔎 Lancement de la détection...")
    
    try:
        pois = detector._extract_from_bbox(
            bbox,
            poi_types,
            tags_config,
            max(DEFAULT_RADII.values()) / 1000,  # Convertir en km
            max_tags_per_type=MAX_TAGS_PER_TYPE
        )
        
        print(f"\n✅ {len(pois)} POI détectés:")
        
        # Statistiques par type
        by_type = {}
        for poi in pois:
            by_type[poi.type] = by_type.get(poi.type, 0) + 1
        
        for poi_type, count in by_type.items():
            print(f"  • {poi_type}: {count}")
        
        # Détail des premiers POI
        print(f"\n📋 Détail des premiers POI:")
        for i, poi in enumerate(pois[:10], 1):
            print(f"  {i}. {poi.name or 'Sans nom'}")
            print(f"     Type: {poi.type}")
            print(f"     Lat: {poi.lat:.6f}, Lon: {poi.lon:.6f}")
            if poi.tags:
                important_tags = {k: v for k, v in poi.tags.items() 
                                if k in ['amenity', 'tourism', 'shop', 'natural', 'drinking_water']}
                if important_tags:
                    print(f"     Tags: {important_tags}")
            print()
        
        # Statistiques
        stats = detector.get_poi_statistics(pois)
        print(f"📊 Statistiques:")
        print(f"  • Total: {stats['total']}")
        print(f"  • Nommés: {stats['named']}")
        print(f"  • Non nommés: {stats['unnamed']}")
        
        if stats['distances']['avg'] is not None:
            print(f"  • Distance min: {stats['distances']['min']:.3f} km")
            print(f"  • Distance max: {stats['distances']['max']:.3f} km")
            print(f"  • Distance moy: {stats['distances']['avg']:.3f} km")
        
        print(f"\n📈 Répartition par type OSM:")
        for osm_type, count in stats['by_osm_type'].items():
            print(f"  • {osm_type}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_osm_tags()
    print("\n" + "="*60)
    print("✅ TEST RÉUSSI" if success else "❌ TEST ÉCHOUÉ")
    print("="*60)