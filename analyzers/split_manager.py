#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging
import math

from config import GPX_DIR, MAX_GPX_DISTANCE_KM, GPX_AUTO_SPLIT

logger = logging.getLogger(__name__)

class SplitManager:
    """Gestionnaire du split intelligent des traces"""
    
    @staticmethod
    def process_split(gpx_processor, total_distance: float, original_file_name: str, analysis_id: str) -> Tuple[List[Dict], int, List[Dict]]:
        """
        Traite le split intelligent de la trace si necessaire
        
        Args:
            gpx_processor: Instance de GPXProcessor
            total_distance: Distance totale en km
            analysis_id: ID de l'analyse
            
        Returns:
            (track_points, segments_count, segment_info)
        """
        track_points = gpx_processor.track_points
        segments_count = 1
        segment_info = []
        
        # Verifier si le split est necessaire
        if total_distance <= MAX_GPX_DISTANCE_KM or not GPX_AUTO_SPLIT:
            logger.info(f"Split non necessaire: {total_distance:.1f} km <= {MAX_GPX_DISTANCE_KM} km")
            return track_points, segments_count, segment_info
        
        # === SPLIT INTELLIGENT ===
        # Calcul du nombre de segments
        num_segments = math.ceil(total_distance / MAX_GPX_DISTANCE_KM)
        segment_distance = total_distance / num_segments
        
        logger.info(f"Split intelligent: {total_distance:.1f} km -> {num_segments} segments de ~{segment_distance:.1f} km")
        
        # Normaliser le nom du fichier source pour eviter des chemins absolus
        original_file_name = Path(original_file_name).stem

        # Decoupage en segments de distance approx. egale
        track_segments = SplitManager._split_intelligent(gpx_processor, num_segments)
        segments_count = len(track_segments)
        
        # Sauvegarde des segments
        segments_dir = GPX_DIR / analysis_id / 'segments'
        segments_dir.mkdir(parents=True, exist_ok=True)
        
        for i, seg in enumerate(track_segments, 1):
            seg_path = segments_dir / f'{original_file_name}_segment_{i:03d}.gpx'
            gpx_processor.save_gpx(seg, seg_path)
            logger.info(f"Segment {i}/{segments_count} sauvegarde: {seg_path} ({len(seg)} points)")
            
            # Calcul distance reelle du segment
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
        
        # Fusionner tous les segments en une seule liste de points
        track_points = []
        for seg in track_segments:
            track_points.extend(seg)
        
        logger.info(f"Split termine: {segments_count} segments crees")
        return track_points, segments_count, segment_info
    
    @staticmethod
    def _split_intelligent(gpx_processor, num_segments: int) -> List[List[Dict[str, Any]]]:
        """
        Divise la trace en segments de distance approx. egale
        
        Args:
            gpx_processor: Instance de GPXProcessor
            num_segments: Nombre de segments souhaites
            
        Returns:
            Liste des segments
        """
        track_points = gpx_processor.track_points
        
        if num_segments <= 1 or len(track_points) < 2:
            return [track_points]
        
        # Calcul de la distance totale
        total_distance = 0.0
        distances = []
        for i in range(1, len(track_points)):
            p1 = track_points[i-1]
            p2 = track_points[i]
            dist = gpx_processor._haversine_distance(
                p1['latitude'], p1['longitude'],
                p2['latitude'], p2['longitude']
            )
            distances.append(dist)
            total_distance += dist
        
        # Distance cible par segment
        target_distance = total_distance / num_segments
        
        segments = []
        current_segment = []
        accumulated = 0.0
        current_target = target_distance
        
        for i, point in enumerate(track_points):
            if not current_segment:
                current_segment.append(point)
                continue
            
            # Ajouter le point au segment courant
            current_segment.append(point)
            
            # Si on a atteint ou depasse la distance cible
            if i < len(track_points) - 1:
                # Calculer la distance depuis le debut du segment
                seg_start = track_points[current_segment[0]['index'] if 'index' in current_segment[0] else 0]
                # Simplification: utiliser la distance accumulee depuis le debut
                # On utilise la distance totale parcourue jusqu'a ce point
                current_dist = sum(distances[:i])
                if current_dist >= current_target and len(segments) < num_segments - 1:
                    segments.append(current_segment)
                    current_segment = []
                    current_target += target_distance
        
        # Ajouter le dernier segment
        if current_segment:
            segments.append(current_segment)
        
        # Si le nombre de segments n'est pas correct, ajuster
        if len(segments) != num_segments:
            logger.warning(f"Nombre de segments: {len(segments)} attendu: {num_segments}")
            # Fallback: diviser en parts egales par points
            if len(segments) < num_segments:
                # Re-diviser en parts egales
                step = len(track_points) // num_segments
                segments = []
                for i in range(0, len(track_points), step):
                    seg = track_points[i:i+step]
                    if seg:
                        segments.append(seg)
        
        return segments
    
    @staticmethod
    def get_split_info(enabled: bool, segments_count: int = 0, segment_info: Optional[List[Dict]] = None) -> Dict:
        """Retourne les informations de split"""
        if enabled:
            return {
                'enabled': True,
                'threshold_km': MAX_GPX_DISTANCE_KM,
                'max_distance_km': round(MAX_GPX_DISTANCE_KM, 1),
                'segments_count': segments_count,
                'segments': segment_info if segment_info is not None else [],
                'reason': 'NA'
            }
        return {
            'enabled': False,
            'threshold_km': MAX_GPX_DISTANCE_KM,
            'max_distance_km': round(MAX_GPX_DISTANCE_KM, 1),
            'segments_count': 'NA',
            'segments': [],
            'reason': 'Distance inferieure au seuil'
        }