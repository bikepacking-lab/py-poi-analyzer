#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import gpxpy
import gpxpy.gpx
from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

class GPXGenerator(BaseGenerator):
    """Générateur de GPX enrichi"""

    def get_format_type(self) -> str:
        return 'gpx-enriched'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """
        Génère un GPX enrichi avec les POI
        
        Args:
            data: Données de l'analyse
            output_dir: REPORT_DIR/analysis_id (dossier de l'analyse)
        """
        
        # 1. Générer le GPX original enrichi
        original_file = self._generate_enriched_gpx(data, output_dir, suffix="")
        
        # 2. Vérifier si des segments existent
        summary = data.get('summary', {})
        split_info = summary.get('split_info', {})
        
        if split_info.get('enabled', False):
            segments = split_info.get('segments', [])
            if segments:
                logger.info(f"Generation des GPX enrichis pour {len(segments)} segments")
                
                # Générer un GPX enrichi pour chaque segment
                for seg_info in segments:
                    segment_path = Path(seg_info.get('file'))
                    if segment_path.exists():
                        self._generate_segment_gpx(segment_path, output_dir, data)
        
        return original_file

    def _generate_enriched_gpx(self, data: Dict[str, Any], output_dir: Path, suffix: str = "") -> Optional[Path]:
        """Génère un GPX enrichi avec les POI"""
        try:
            track_points = data.get('track_points', [])
            pois = data.get('pois', [])
            
            if not track_points:
                logger.warning("Aucun point de trace pour le GPX enrichi")
                return None

            gpx = gpxpy.gpx.GPX()
            
            # Trace
            if track_points:
                gpx_track = gpxpy.gpx.GPXTrack()
                gpx.tracks.append(gpx_track)
                
                gpx_segment = gpxpy.gpx.GPXTrackSegment()
                gpx_track.segments.append(gpx_segment)
                
                for point_data in track_points:
                    point = gpxpy.gpx.GPXTrackPoint(
                        point_data.get('latitude', 0),
                        point_data.get('longitude', 0),
                        elevation=point_data.get('elevation'),
                        time=point_data.get('time')
                    )
                    gpx_segment.points.append(point)
            
            # POI (Waypoints)
            for i, poi in enumerate(pois):
                name = poi.get('name') or f"POI_{poi.get('type', 'unknown')}_{i+1}"
                
                waypoint = gpxpy.gpx.GPXWaypoint(
                    latitude=poi.get('lat', 0),
                    longitude=poi.get('lon', 0),
                    name=name,
                    description=f"Type: {poi.get('type', 'unknown')}, Distance: {poi.get('distance', 0):.2f} km",
                    symbol=f"poi_{poi.get('type', 'unknown')}"
                )
                gpx.waypoints.append(waypoint)
            
            # Nom du fichier dans REPORT_DIR/analysis_id/
            analysis_id = data.get('analysis_id', 'unknown')
            filename = f"enriched_track_{analysis_id}{suffix}.gpx"
            output_file = output_dir / filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPX enrichi genere: {output_file} ({len(track_points)} points, {len(pois)} POI)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur GPX enrichi: {e}")
            return None

    def _generate_segment_gpx(self, segment_path: Path, output_dir: Path, data: Dict[str, Any]) -> Optional[Path]:
        """
        Génère un GPX enrichi pour un segment spécifique
        
        Args:
            segment_path: Chemin du fichier GPX du segment (dans GPX_DIR)
            output_dir: REPORT_DIR/analysis_id (dossier de l'analyse)
            data: Données de l'analyse
        """
        try:
            # Charger le segment GPX
            with open(segment_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            
            # Extraire les points du segment
            segment_points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        segment_points.append({
                            'latitude': point.latitude,
                            'longitude': point.longitude,
                            'elevation': point.elevation,
                            'time': point.time
                        })
            
            if not segment_points:
                logger.warning(f"Segment vide: {segment_path}")
                return None
            
            # Filtrer les POI proches du segment
            pois = data.get('pois', [])
            segment_pois = self._filter_pois_near_segment(segment_points, pois)
            
            # Créer le GPX enrichi du segment
            enriched_gpx = gpxpy.gpx.GPX()
            
            # Trace du segment
            gpx_track = gpxpy.gpx.GPXTrack()
            enriched_gpx.tracks.append(gpx_track)
            
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            
            for point_data in segment_points:
                point = gpxpy.gpx.GPXTrackPoint(
                    point_data.get('latitude', 0),
                    point_data.get('longitude', 0),
                    elevation=point_data.get('elevation'),
                    time=point_data.get('time')
                )
                gpx_segment.points.append(point)
            
            # POI du segment
            for i, poi in enumerate(segment_pois):
                name = poi.get('name') or f"POI_{poi.get('type', 'unknown')}_{i+1}"
                
                waypoint = gpxpy.gpx.GPXWaypoint(
                    latitude=poi.get('lat', 0),
                    longitude=poi.get('lon', 0),
                    name=name,
                    description=f"Type: {poi.get('type', 'unknown')}, Distance: {poi.get('distance', 0):.2f} km",
                    symbol=f"poi_{poi.get('type', 'unknown')}"
                )
                enriched_gpx.waypoints.append(waypoint)
            
            # Sauvegarder dans REPORT_DIR/analysis_id/
            segment_name = segment_path.stem
            filename = f"{segment_name}_enriched.gpx"
            output_file = output_dir / filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(enriched_gpx.to_xml())
            
            logger.info(f"GPX enrichi segment genere: {output_file} ({len(segment_points)} points, {len(segment_pois)} POI)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur generation GPX segment enrichi: {e}")
            return None

    def _filter_pois_near_segment(self, segment_points: List[Dict], pois: List[Dict], max_distance_km: float = 5.0) -> List[Dict]:
        """
        Filtre les POI proches d'un segment
        
        Args:
            segment_points: Points du segment
            pois: Liste des POI
            max_distance_km: Distance maximale en km pour inclure un POI
        
        Returns:
            Liste des POI filtrés
        """
        if not segment_points or not pois:
            return []
        
        # Calculer le centroïde du segment
        lats = [p['latitude'] for p in segment_points]
        lons = [p['longitude'] for p in segment_points]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Filtrer les POI par distance au centroïde
        from core.gpx_processor import GPXProcessor
        processor = GPXProcessor()
        
        filtered_pois = []
        for poi in pois:
            dist = processor._haversine_distance(
                center_lat, center_lon,
                poi.get('lat', 0), poi.get('lon', 0)
            )
            if dist <= max_distance_km:
                filtered_pois.append(poi)
        
        return filtered_pois