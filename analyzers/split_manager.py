#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Any
import logging
from config import MAX_GPX_DISTANCE_KM, GPX_AUTO_SPLIT
from config import GPX_DIR, CHUNK_DISTANCE_KM

logger = logging.getLogger(__name__)

class SplitManager:
    """Gestionnaire du split des traces"""
    
    @staticmethod
    def process_split(gpx_processor, total_distance: float, analysis_id: str) -> Tuple[List[Dict], int, List[Dict]]:
        """
        Traite le split de la trace si necessaire
        
        Returns:
            (track_points, segments_count, segment_info)
        """
        
        track_points = gpx_processor.track_points
        segments_count = 1
        segment_info = []
        
        if total_distance > MAX_GPX_DISTANCE_KM and GPX_AUTO_SPLIT:
            logger.info(f"Trace divisee en segments de {CHUNK_DISTANCE_KM} km")
            track_segments = gpx_processor.split_track(CHUNK_DISTANCE_KM)
            segments_count = len(track_segments)
            
            segments_dir = GPX_DIR / analysis_id / 'segments'
            segments_dir.mkdir(parents=True, exist_ok=True)
            
            for i, seg in enumerate(track_segments, 1):
                seg_path = segments_dir / f'segment_{i:03d}.gpx'
                gpx_processor.save_gpx(seg, seg_path)
                
                seg_dist = 0.0
                for j in range(1, len(seg)):
                    p1 = seg[j-1]
                    p2 = seg[j]
                    seg_dist += gpx_processor._haversine_distance(
                        p1['latitude'], p1['longitude'],
                        p2['latitude'], p2['longitude']
                    )
                
                segment_info.append({
                    'id': i,
                    'file': str(seg_path),
                    'points': len(seg),
                    'distance_km': round(seg_dist, 2)
                })
            
            track_points = []
            for seg in track_segments:
                track_points.extend(seg)
        
        return track_points, segments_count, segment_info
    
    @staticmethod
    def get_split_info(segment_info: List[Dict], enabled: bool, segments_count: int = 0) -> Dict:
        """Retourne les informations de split"""
        if enabled:
            return {
                'enabled': True,
                'max_distance_km': CHUNK_DISTANCE_KM,
                'segments_count': segments_count,
                'segments': segment_info or []
            }
        return {
            'enabled': False,
            'reason': 'Auto-split desactive'
        }