#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gpxpy
import gpxpy.gpx
from typing import List, Tuple, Dict, Any
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
            self._calculate_elevation_stats()
            logger.info(f"GPX charge: {file_path}, {len(self.track_points)} points")
            
            elevation = self.get_elevation_stats()
            if elevation.get('total_ascent_m', 0) > 0:
                logger.info(f"Denivele: +{elevation['total_ascent_m']:.0f}m / -{elevation['total_descent_m']:.0f}m")
                logger.info(f"  (seuil={ELEVATION_MIN_VARIATION}m, lissage={ELEVATION_SMOOTHING_WINDOW}pts, subsample={ELEVATION_SUBSAMPLE_STEP})")
            return True
        except Exception as e:
            logger.error(f"Erreur chargement GPX: {e}")
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
                        'elevation': point.elevation,
                        'time': point.time,
                        'distance': 0.0
                    })
        return points
    
    def _calculate_elevation_stats(self):
        """
        Calcule les statistiques d'elevation avec les parametres config
        Correspond a visugpx : seuil=10m, lissage=5pts, subsample=1/3
        """
        elevations = []
        for point in self.track_points:
            if point.get('elevation') is not None:
                elevations.append(point['elevation'])
        
        if not elevations:
            self.min_elevation = None
            self.max_elevation = None
            self.total_ascent = 0.0
            self.total_descent = 0.0
            return
        
        self.min_elevation = min(elevations)
        self.max_elevation = max(elevations)
        
        # === 1. SOUS-ECHANTILLONNAGE (1 point sur 3) ===
        # Visugpx fait cela pour les longues traces
        if len(self.track_points) > ELEVATION_SUBSAMPLE_THRESHOLD:
            step = ELEVATION_SUBSAMPLE_STEP
            points = self.track_points[::step]
            logger.debug(f"Sous-echantillonnage: {len(self.track_points)} -> {len(points)} points (step={step})")
        else:
            points = self.track_points
        
        # === 2. LISSAGE SUR 5 POINTS ===
        window_size = ELEVATION_SMOOTHING_WINDOW
        half_window = window_size // 2
        smoothed = []
        
        for i in range(len(points)):
            if points[i].get('elevation') is None:
                smoothed.append(None)
                continue
            
            window = []
            for j in range(max(0, i - half_window), min(len(points), i + half_window + 1)):
                if points[j].get('elevation') is not None:
                    window.append(points[j]['elevation'])
            
            if window:
                smoothed.append(sum(window) / len(window))
            else:
                smoothed.append(None)
        
        # === 3. SEUIL MINIMUM ===
        min_variation = ELEVATION_MIN_VARIATION
        
        self.total_ascent = 0.0
        self.total_descent = 0.0
        
        for i in range(1, len(smoothed)):
            if smoothed[i] is None or smoothed[i-1] is None:
                continue
            
            diff = smoothed[i] - smoothed[i-1]
            
            # Ignorer les variations inferieures au seuil
            if abs(diff) < min_variation:
                continue
                
            if diff > 0:
                self.total_ascent += diff
            else:
                self.total_descent += abs(diff)
        
        # Arrondir a l'entier
        self.total_ascent = round(self.total_ascent, 0)
        self.total_descent = round(self.total_descent, 0)
    
    def get_elevation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'elevation"""
        return {
            'min_elevation_m': self.min_elevation,
            'max_elevation_m': self.max_elevation,
            'total_ascent_m': self.total_ascent,
            'total_descent_m': self.total_descent
        }
        
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
    
    def get_total_distance(self) -> float:
        """Distance totale en km"""
        distances = self.calculate_distances()
        return sum(distances) if distances else 0.0
    
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
        """
        Genere des bbox pour la recherche POI - OPTIMISE
        
        Args:
            interval_km: Intervalle en km defini par l'utilisateur
        """
        if not self.track_points:
            return []
        
        bboxes = []
        
        # AUGMENTER LE NOMBRE DE POINTS PAR SEGMENT pour reduire le nombre de bboxes
        # Plus l'intervalle est grand, moins il y a de bboxes
        points_per_segment = max(30, int(interval_km * 20))  # 30 points minimum
        
        # Echantillonnage pour reduire encore le nombre de points
        # Prendre 1 point sur 2 pour les longues traces
        if len(self.track_points) > 5000:
            step = 2
            points = self.track_points[::step]
            logger.info(f"Echantillonnage: {len(self.track_points)} -> {len(points)} points (step={step})")
        else:
            points = self.track_points
        
        for i in range(0, len(points), points_per_segment):
            segment_points = points[i:i+points_per_segment]
            if len(segment_points) < 3:
                continue
            
            lats = [p['latitude'] for p in segment_points]
            lons = [p['longitude'] for p in segment_points]
            
            # Padding adaptatif plus petit
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            padding = max(0.001, (lat_range + lon_range) / 6.0)  # Padding reduit
            padding = min(padding, 0.005)  # Max 500m de padding
            
            bbox = (
                float(min(lats) - padding),
                float(min(lons) - padding),
                float(max(lats) + padding),
                float(max(lons) + padding)
            )
            bboxes.append(bbox)
        
        logger.info(f"Genere {len(bboxes)} bboxes (intervalle: {interval_km}km, points/segment: {points_per_segment})")
        return bboxes