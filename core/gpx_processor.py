#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gpxpy
import gpxpy.gpx
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import logging
import math

from config import (
    ELEVATION_MIN_VARIATION,
    ELEVATION_SMOOTHING_WINDOW,
    ELEVATION_SUBSAMPLE_STEP,
    ELEVATION_SUBSAMPLE_THRESHOLD
)

logger = logging.getLogger(__name__)

class GPXProcessor:
    """Processeur de fichiers GPX"""
    
    def __init__(self):
        self.gpx = None
        self.file_path = None
        self.track_points = []
        self.total_ascent = 0.0
        self.total_descent = 0.0
        self.min_elevation = None
        self.max_elevation = None
    
    def load_gpx(self, file_path: Path) -> bool:
        """Charge un fichier GPX"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.gpx = gpxpy.parse(f)
            self.file_path = file_path
            self.track_points = self._extract_track_points()
            
            # DEBUG: Afficher les stats des elevations
            elevations = [p.get('elevation') for p in self.track_points if p.get('elevation') is not None]
            logger.info(f"Total points: {len(self.track_points)}, avec elevation: {len(elevations)}")
            if elevations:
                logger.info(f"Elevation min: {min(elevations):.1f}, max: {max(elevations):.1f}")
            
            # Calculer les distances
            self.calculate_distances()
            
            # Calculer les stats d'elevation
            self._calculate_elevation_stats()
            
            logger.info(f"GPX charge: {file_path}, {len(self.track_points)} points")
            
            elevation = self.get_elevation_stats()
            if elevation.get('total_ascent_m', 0) > 0:
                logger.info(f"Denivele: +{elevation['total_ascent_m']:.0f}m / -{elevation['total_descent_m']:.0f}m")
            else:
                logger.warning("Denivele nul ou non calcule")
            return True
        except Exception as e:
            logger.error(f"Erreur chargement GPX: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _extract_track_points(self) -> List[Dict[str, Any]]:
        """Extrait tous les points de la trace"""
        points = []
        if not self.gpx:
            return points
        
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append({
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation if point.elevation is not None else None,
                        'time': point.time,
                        'distance': 0.0
                    })
        return points
    
    def calculate_distances(self) -> List[float]:
        """Calcule les distances entre les points"""
        if len(self.track_points) < 2:
            return []
        
        distances = []
        cumulative = 0.0
        for i in range(1, len(self.track_points)):
            p1 = self.track_points[i-1]
            p2 = self.track_points[i]
            dist = self._haversine_distance(
                p1['latitude'], p1['longitude'],
                p2['latitude'], p2['longitude']
            )
            cumulative += dist
            distances.append(dist)
            self.track_points[i]['distance'] = cumulative
        
        return distances
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance en km avec Haversine"""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
        return R * c
    
    def _calculate_elevation_stats(self):
        """
        Calcule les statistiques d'elevation
        """
        # === 1. COLLECTER LES ELEVATIONS ===
        elevations = []
        for point in self.track_points:
            elev = point.get('elevation')
            if elev is not None and elev != 0:
                elevations.append(elev)
    
        if not elevations:
            logger.warning("Aucune elevation valide trouvee")
            self.min_elevation = None
            self.max_elevation = None
            self.total_ascent = 0.0
            self.total_descent = 0.0
            return
    
        # === STOCKER LES ALTITUDES ===
        self.min_elevation = min(elevations)
        self.max_elevation = max(elevations)
    
        logger.info(f"Elevation min: {self.min_elevation:.0f}m, max: {self.max_elevation:.0f}m")
        logger.info(f"Nombre de points avec elevation: {len(elevations)}")
    
        # === 2. SOUS-ECHANTILLONNAGE ===
        if len(elevations) > ELEVATION_SUBSAMPLE_THRESHOLD:
            step = ELEVATION_SUBSAMPLE_STEP
            elevations = elevations[::step]
            logger.debug(f"Sous-echantillonnage: {len(elevations)} points")
    
        # === 3. LISSAGE ===
        window_size = ELEVATION_SMOOTHING_WINDOW
        smoothed = []
    
        for i in range(len(elevations)):
            start = max(0, i - window_size // 2)
            end = min(len(elevations), i + window_size // 2 + 1)
            window = elevations[start:end]
            if window:
                smoothed.append(sum(window) / len(window))
            else:
                smoothed.append(elevations[i])
    
        # === 4. SEUIL ADAPTATIF ===
        diffs = []
        for i in range(1, len(smoothed)):
            diff = abs(smoothed[i] - smoothed[i-1])
            if diff > 0:
                diffs.append(diff)
    
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            min_variation = max(1.0, avg_diff * 0.5)
            logger.info(f"Variation moyenne: {avg_diff:.2f}m, seuil: {min_variation:.2f}m")
        else:
            min_variation = ELEVATION_MIN_VARIATION
    
        self.total_ascent = 0.0
        self.total_descent = 0.0
        variations_count = 0
    
        for i in range(1, len(smoothed)):
            diff = smoothed[i] - smoothed[i-1]
        
            if abs(diff) < min_variation:
                continue
        
            variations_count += 1
        
            if diff > 0:
                self.total_ascent += diff
            else:
                self.total_descent += abs(diff)
    
        self.total_ascent = round(self.total_ascent, 0)
        self.total_descent = round(self.total_descent, 0)
    
        logger.info(f"Variations > {min_variation:.1f}m: {variations_count}")
        logger.info(f"Denivele: +{self.total_ascent:.0f}m / -{self.total_descent:.0f}m")

    def get_elevation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'elevation"""
        return {
            'min_altitude_m': self.min_elevation,    # <-- CORRECTION: min_altitude_m
            'max_altitude_m': self.max_elevation,    # <-- CORRECTION: max_altitude_m
            'total_ascent_m': self.total_ascent,
            'total_descent_m': self.total_descent
        }
    
    def get_total_distance(self) -> float:
        """Distance totale en km"""
        return self.track_points[-1].get('distance', 0.0) if self.track_points else 0.0
    
    def get_track_bounds(self) -> Tuple[float, float, float, float]:
        """Limites de la trace (bbox)"""
        if not self.track_points:
            return (0.0, 0.0, 0.0, 0.0)
        
        lats = [p['latitude'] for p in self.track_points]
        lons = [p['longitude'] for p in self.track_points]
        return (min(lats), min(lons), max(lats), max(lons))
    
    def split_track(self, max_distance_km: float) -> List[List[Dict[str, Any]]]:
        """Divise la trace en segments"""
        if not self.track_points:
            return []
        
        segments = []
        current_segment = []
        accumulated_distance = 0.0
        
        for point in self.track_points:
            if not current_segment:
                current_segment.append(point)
                continue
            
            last_point = current_segment[-1]
            dist = self._haversine_distance(
                last_point['latitude'], last_point['longitude'],
                point['latitude'], point['longitude']
            )
            
            if accumulated_distance + dist > max_distance_km:
                if current_segment:
                    segments.append(current_segment.copy())
                current_segment = [point]
                accumulated_distance = 0.0
            else:
                current_segment.append(point)
                accumulated_distance += dist
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def save_gpx(self, points: List[Dict[str, Any]], output_path: Path) -> bool:
        """Sauvegarde des points en GPX"""
        try:
            gpx = gpxpy.gpx.GPX()
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            for point_data in points:
                point = gpxpy.gpx.GPXTrackPoint(
                    point_data['latitude'],
                    point_data['longitude'],
                    elevation=point_data.get('elevation'),
                    time=point_data.get('time')
                )
                gpx_segment.points.append(point)
            
            gpx_track.segments.append(gpx_segment)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPX sauvegarde: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde GPX: {e}")
            return False
    
    def get_poi_search_segments(self, interval_km: float) -> List[Tuple[float, float, float, float]]:
        """Genere des bbox pour la recherche POI"""
        if not self.track_points:
            return []
        
        bboxes = []
        points_per_segment = max(30, int(interval_km * 20))
        
        if len(self.track_points) > 5000:
            step = 2
            points = self.track_points[::step]
        else:
            points = self.track_points
        
        for i in range(0, len(points), points_per_segment):
            segment_points = points[i:i+points_per_segment]
            if len(segment_points) < 3:
                continue
            
            lats = [p['latitude'] for p in segment_points]
            lons = [p['longitude'] for p in segment_points]
            
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            padding = max(0.001, (lat_range + lon_range) / 6.0)
            padding = min(padding, 0.005)
            
            bbox = (
                float(min(lats) - padding),
                float(min(lons) - padding),
                float(max(lats) + padding),
                float(max(lons) + padding)
            )
            bboxes.append(bbox)
        
        return bboxes