#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Optional
import logging

from core.poi_detector import POI

logger = logging.getLogger(__name__)

class StatsManager:
    """Gestionnaire des statistiques"""
    
    @staticmethod
    def get_safe_poi_stats(pois: Optional[List[POI]], poi_detector) -> Dict[str, Any]:
        """
        Recupere les statistiques POI de maniere sure
        """
        if not pois:
            return {
                'total': 0,
                'by_type': {},
                'by_osm_type': {},
                'named': 0,
                'unnamed': 0,
                'distances': None
            }
        
        try:
            stats = poi_detector.get_poi_statistics(pois)
            if not isinstance(stats, dict):
                return StatsManager._default_stats(len(pois))
            return stats
        except Exception as e:
            logger.error(f"Erreur recuperation stats POI: {e}")
            return StatsManager._default_stats(len(pois))
    
    @staticmethod
    def _default_stats(total: int) -> Dict[str, Any]:
        """Statistiques par defaut"""
        return {
            'total': total,
            'by_type': {},
            'by_osm_type': {},
            'named': 0,
            'unnamed': 0,
            'distances': None
        }
    
    @staticmethod
    def safe_get_distances(poi_stats: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Extrait les distances des statistiques POI de maniere sure
        """
        if not poi_stats:
            return None
        
        distances = poi_stats.get('distances')
        
        if distances is None or not isinstance(distances, dict):
            return None
        
        min_val = distances.get('min')
        max_val = distances.get('max')
        avg_val = distances.get('avg')
        
        if min_val is None or max_val is None or avg_val is None:
            return None
        
        try:
            return {
                'min_km': round(float(min_val), 3),
                'max_km': round(float(max_val), 3),
                'avg_km': round(float(avg_val), 3)
            }
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def build_track_info(track_points: List[Dict]) -> Dict[str, Any]:
        """Construit les informations de la trace"""
        return {
            'total_points': len(track_points),
            'has_elevation': any(p.get('elevation') is not None for p in track_points[:100]),
            'has_time': any(p.get('time') is not None for p in track_points[:100])
        }
    
    @staticmethod
    def build_poi_results(poi_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Construit les resultats des POI"""
        return {
            'total_found': poi_stats.get('total', 0),
            'by_type': poi_stats.get('by_type', {}),
            'by_osm_type': poi_stats.get('by_osm_type', {}),
            'named_count': poi_stats.get('named', 0),
            'unnamed_count': poi_stats.get('unnamed', 0)
        }