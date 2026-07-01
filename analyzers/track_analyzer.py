#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import time

from config import (
    MAX_GPX_DISTANCE_KM, ANALYSIS_MAX_PARALLEL,
    REPORT_DIR, DEFAULT_POI_TYPES, DEFAULT_RADII,
    DEFAULT_INTERVALS, DEFAULT_REPORT_FORMATS,
    DEFAULT_POI_TAGS_OSM, MAX_TAGS_PER_TYPE
)
from core.gpx_processor import GPXProcessor
from core.poi_detector import POIDetector
from core.cache_manager import get_cache_manager
from generators import GeneratorRegistry

from .file_manager import FileManager
from .stats_manager import StatsManager
from .recommendation_manager import RecommendationManager
from .split_manager import SplitManager

logger = logging.getLogger(__name__)

class TrackAnalyzer:
    """Analyseur de trace GPS - Orchestrateur principal"""
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.poi_detector = POIDetector(self.cache)
        self.analysis_id = ""
        self.analysis_dir = REPORT_DIR
        self.start_time = 0.0
    
    def analyze(self, input_file: Path, 
               poi_types: Optional[List[str]] = None,
               radii: Optional[Dict[str, float]] = None,
               intervals: Optional[Dict[str, float]] = None,
               report_formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """Point d'entree principal pour l'analyse"""
        
        # Initialisation
        self.start_time = time.time()
        self.analysis_id = str(uuid.uuid4())
        self.analysis_dir = REPORT_DIR / self.analysis_id
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"=== DEBUT ANALYSE {self.analysis_id} ===")
        logger.info(f"Fichier: {input_file}")
        
        # 1. Validation du fichier
        is_valid, error = FileManager.validate_file(input_file)
        if not is_valid:
            raise ValueError(error)
        
        # 2. Sauvegarde du fichier source
        saved_file = FileManager.save_source_file(input_file, self.analysis_id)
        
        # 3. Chargement du GPX
        gpx_processor = GPXProcessor()
        if not gpx_processor.load_gpx(input_file):
            raise ValueError(f"Impossible de charger le GPX: {input_file}")
        
        total_distance = gpx_processor.get_total_distance()
        track_points = gpx_processor.track_points
        
        logger.info(f"Distance totale: {total_distance:.2f} km, Points: {len(track_points)}")
        
        # 4. Split si necessaire
        track_points, segments_count, segment_info = SplitManager.process_split(
            gpx_processor, total_distance, self.analysis_id
        )
        
        search_start = time.time()
        
        # 5. Detection POI - Utilisation des valeurs par defaut si non fournies
        poi_types = poi_types or DEFAULT_POI_TYPES
        radii = radii or DEFAULT_RADII
        intervals = intervals or DEFAULT_INTERVALS
        
        all_bboxes = []
        bboxes_by_type = {}

        search_start = time.time()
        
        for poi_type in poi_types:
            interval = intervals.get(poi_type, 20.0)
            logger.info(f"Bboxes pour '{poi_type}': intervalle {interval} km")
    
            bboxes = gpx_processor.get_poi_search_segments(interval)
            bboxes_by_type[poi_type] = bboxes
            all_bboxes.extend(bboxes)
        
        unique_bboxes = list(set(all_bboxes))
        logger.info(f"Total: {len(unique_bboxes)} bboxes uniques")
           
        search_duration = time.time() - search_start
        if unique_bboxes:
            pois = self.poi_detector.detect_pois(
                unique_bboxes, poi_types, DEFAULT_POI_TAGS_OSM, radii,
                max_workers=ANALYSIS_MAX_PARALLEL,
                max_tags_per_type=MAX_TAGS_PER_TYPE
            )
        else:
            pois = []
            logger.warning("Aucune bbox generee")
    
        logger.info(f"{len(pois)} POI detectes en {search_duration:.2f}s")
        
        search_duration = time.time() - search_start
        
        dist_start = time.time()
        
        # 6. Calcul des distances
        if pois and track_points:
            dist_start = time.time()
            pois = self.poi_detector.calculate_distances_to_track(pois, track_points)
            dist_duration = time.time() - dist_start
        else:
            dist_duration = 0
        
        dist_duration = time.time() - dist_start
        
        # 7. Statistiques
        poi_stats = StatsManager.get_safe_poi_stats(pois, self.poi_detector)
        
        # 8. Construction du resume
        stats = self._build_summary(
            input_file, saved_file, gpx_processor, total_distance,
            track_points, segments_count, segment_info,
            bboxes, poi_stats, search_duration, dist_duration,
            poi_types, radii, intervals
        )
        stats['poi_search']['configuration'] = {
            'types': poi_types,
            'radii': radii,
            'intervals': intervals,
            'poi_api_url': 'https://overpass-api.de/api/interpreter'
        }
        stats['poi_search']['bboxes_count'] = len(unique_bboxes)
        stats['poi_search']['bboxes_by_type'] = {t: len(b) for t, b in bboxes_by_type.items()}
        
        report_start = time.time()
        
        # 9. Generation des rapports
        report_formats = report_formats if report_formats else DEFAULT_REPORT_FORMATS
        
        logger.info(f"Generation des rapports: {report_formats}")
        
        reports = self._generate_reports(
            input_file, saved_file, track_points, pois,
            total_distance, segments_count, poi_types,
            radii, intervals, stats, report_formats
        )
        
        report_duration = time.time() - report_start
        
        # 10. Sauvegarde du summary
        self._save_summary(input_file, saved_file, stats, reports)
        
        total_duration = time.time() - self.start_time
        
        stats['performance'] = {
            'total_duration_seconds': round(total_duration, 2),
            'search_duration_seconds': round(search_duration, 2),
            'distance_calculation_seconds': round(dist_duration, 2),
            'report_generation_seconds': round(report_duration, 2)
        }
        
        # 11. Resultats
        results = {
            'analysis_id': self.analysis_id,
            'analysis_dir': str(self.analysis_dir),
            'input_file': str(input_file),
            'input_file_saved': str(saved_file) if saved_file else None,
            'total_distance': total_distance,
            'num_pois': poi_stats.get('total', 0),
            'pois_by_type': poi_stats.get('by_type', {}),
            'reports': reports,
            'summary': stats
        }
        
        logger.info(f"=== FIN ANALYSE {self.analysis_id} ===")
        logger.info(f"Resume: {poi_stats.get('total', 0)} POI, {total_distance:.2f} km")
        logger.info(f"Rapports generes: {list(reports.keys())}")
        
        return results
    
    def _build_summary(self, input_file, saved_file, gpx_processor, total_distance,
                      track_points, segments_count, segment_info,
                      bboxes, poi_stats, search_duration, dist_duration,
                      poi_types, radii, intervals) -> Dict:
        """Construit le resume de l'analyse"""
        
        # File info
        file_info = FileManager.get_file_info(input_file)
        if saved_file:
            file_info['saved_to'] = str(saved_file)
        
        elevation_stats = gpx_processor.get_elevation_stats()

        track_info = {
            'total_distance_km': round(total_distance, 2),
            'has_elevation': any(p.get('elevation') is not None for p in gpx_processor.track_points[:100]),
            'has_time': any(p.get('time') is not None for p in gpx_processor.track_points[:100]),
            'min_elevation_m': elevation_stats.get('min_elevation_m'),
            'max_elevation_m': elevation_stats.get('max_elevation_m'),
            'total_ascent_m': elevation_stats.get('total_ascent_m', 0),
            'total_descent_m': elevation_stats.get('total_descent_m', 0),
            **StatsManager.build_track_info(gpx_processor.track_points)
        }
        
        # Split info
        split_info = SplitManager.get_split_info(
            total_distance > MAX_GPX_DISTANCE_KM,
            segments_count,
            segment_info
        )
        
        # POI search
        poi_config = {
            'types': poi_types,
            'radii': radii,
            'intervals': intervals,
            'poi_api_url': 'https://overpass-api.de/api/interpreter'
        }
        
        poi_results = StatsManager.build_poi_results(poi_stats)
        poi_distances = StatsManager.safe_get_distances(poi_stats)
        
        poi_search = {
            'configuration': poi_config,
            'bboxes_count': len(bboxes),
            'duration_seconds': round(search_duration, 2),
            'distance_calculation_seconds': round(dist_duration, 2) if dist_duration > 0 else None,
            'results': poi_results,
            'distances': poi_distances
        }
        
        # Performance
        performance = {
            'total_duration_seconds': round(time.time() - self.start_time, 2),
            'search_duration_seconds': round(search_duration, 2)
        }
        
        # Recommendations
        recommendations = RecommendationManager.generate(poi_stats, poi_types, radii)
        
        return {
            'file_info': file_info,
            'track_info': track_info,
            'split_info': split_info,
            'poi_search': poi_search,
            'performance': performance,
            'recommendations': recommendations
        }
    
    def _generate_reports(self, input_file, saved_file, track_points, pois,
                         total_distance, segments_count, poi_types,
                         radii, intervals, stats, report_formats):
        """Genere les rapports"""
        
        if not report_formats:
            logger.info("Aucun format de rapport demande")
            return {}
        
        report_data = {
            'analysis_id': self.analysis_id,
            'input_file': str(input_file),
            'input_file_saved': str(saved_file) if saved_file else None,
            'timestamp': datetime.now().isoformat(),
            'summary': stats,
            'total_distance': total_distance,
            'num_points': len(track_points),
            'num_segments': segments_count,
            'poi_types': poi_types,
            'radii': radii,
            'intervals': intervals,
            'track_points': track_points,
            'pois': [p.to_dict() for p in pois] if pois else []
        }
        
        reports = {}
        for fmt in report_formats:
            generator = GeneratorRegistry.get_generator(fmt)
            if generator:
                try:
                    file_path = generator.generate(report_data, self.analysis_dir)
                    if file_path:
                        reports[fmt] = str(file_path)
                        logger.info(f"Rapport {fmt} genere: {file_path}")
                except Exception as e:
                    logger.error(f"Erreur generation {fmt}: {e}")
            else:
                logger.warning(f"Generateur non trouve pour le format: {fmt}")
        
        return reports
    
    def _save_summary(self, input_file, saved_file, stats, reports):
        """Sauvegarde le summary JSON"""
        summary_file = self.analysis_dir / f'analysis_report_{self.analysis_id}_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_id': self.analysis_id,
                'generated': datetime.now().isoformat(),
                'input_file': str(input_file),
                'input_file_saved': str(saved_file) if saved_file else None,
                'summary': stats,
                'reports': {k: Path(v).name for k, v in reports.items()}
            }, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Resume sauvegarde: {summary_file}")