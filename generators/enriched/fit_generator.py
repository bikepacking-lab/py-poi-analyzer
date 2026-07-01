#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta

from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

# === TENTATIVE D'IMPORT FITDECODE ===
FIT_AVAILABLE = False
try:
    import fitdecode
    # Vérifier que l'import fonctionne
    if hasattr(fitdecode, 'FitFile') and hasattr(fitdecode, 'FitWriter'):
        FIT_AVAILABLE = True
        logger.info("fitdecode importe avec succes")
    else:
        logger.warning("fitdecode importe mais API incomplete")
except ImportError as e:
    logger.warning(f"fitdecode non disponible: {e}")
except Exception as e:
    logger.warning(f"Erreur import fitdecode: {e}")

# Fallback: essayer d'importer depuis fitdecode
if not FIT_AVAILABLE:
    try:
        from fitdecode import FitFile, FitWriter, Fit
        FIT_AVAILABLE = True
        logger.info("fitdecode importe via fallback")
    except ImportError:
        pass


class FITGenerator(BaseGenerator):
    """Générateur de fichiers FIT enrichis"""

    def get_format_type(self) -> str:
        return 'fit-data'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère un fichier FIT et un JSON de données"""

        output_file = output_dir / f'fit_data_{data.get("analysis_id", "unknown")}.json'
        fit_file = output_dir / f'fit_data_{data.get("analysis_id", "unknown")}.fit'

        try:
            # 1. Préparer les données
            fit_data = self._prepare_fit_data(data)

            # 2. Sauvegarder en JSON (toujours)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fit_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Donnees FIT JSON generees: {output_file}")

            # 3. Générer le fichier FIT binaire
            if FIT_AVAILABLE:
                try:
                    fit_file = self._generate_fit_file(fit_data, fit_file, data)
                    if fit_file and fit_file.exists():
                        logger.info(f"Fichier FIT genere: {fit_file}")
                        return fit_file
                    else:
                        logger.warning("Generation FIT a echoue")
                        return output_file
                except Exception as e:
                    logger.error(f"Erreur generation FIT: {e}")
                    return output_file
            else:
                logger.warning("fitdecode non disponible. Fichier FIT non genere.")
                logger.info("Installez: pip install fitdecode")
                logger.info("Ou utilisez le fichier JSON pour conversion manuelle")
                return output_file

        except Exception as e:
            logger.error(f"Erreur FIT: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _prepare_fit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare les donnees au format FIT"""
        track_points = data.get('track_points', []) or []
        pois = data.get('pois', []) or []
        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})

        fit_data = {
            'metadata': {
                'version': '1.0',
                'generated': datetime.now().isoformat(),
                'analysis_id': data.get('analysis_id', ''),
                'total_distance_km': track_info.get('total_distance_km', 0),
                'total_ascent_m': track_info.get('total_ascent_m', 0),
                'total_descent_m': track_info.get('total_descent_m', 0),
                'min_altitude_m': track_info.get('min_altitude_m', 0),
                'max_altitude_m': track_info.get('max_altitude_m', 0),
                'total_points': len(track_points),
                'total_poi': len(pois)
            },
            'track': {
                'points': [
                    {
                        'latitude': p.get('latitude', 0),
                        'longitude': p.get('longitude', 0),
                        'elevation': p.get('elevation', 0),
                        'distance': p.get('distance', 0),
                        'time': p.get('time', datetime.now().isoformat()) if p.get('time') else datetime.now().isoformat()
                    }
                    for p in track_points
                ]
            },
            'pois': [
                {
                    'id': poi.get('id', ''),
                    'type': poi.get('type', ''),
                    'name': poi.get('name', ''),
                    'latitude': poi.get('lat', 0),
                    'longitude': poi.get('lon', 0),
                    'distance_km': poi.get('distance', 0),
                    'address': poi.get('address', ''),
                    'phone': poi.get('phone', ''),
                    'website': poi.get('website', ''),
                    'opening_hours': poi.get('opening_hours', ''),
                    'description': poi.get('description', ''),
                    'google_maps_url': poi.get('google_maps_url', '')
                }
                for poi in pois
            ],
            'statistics': {
                'by_type': {},
                'named_count': 0,
                'unnamed_count': 0
            }
        }

        for poi in pois:
            poi_type = poi.get('type', 'unknown')
            fit_data['statistics']['by_type'][poi_type] = fit_data['statistics']['by_type'].get(poi_type, 0) + 1
            if poi.get('name'):
                fit_data['statistics']['named_count'] += 1
            else:
                fit_data['statistics']['unnamed_count'] += 1

        return fit_data

    def _generate_fit_file(self, fit_data: Dict[str, Any], output_path: Path, data: Dict[str, Any]) -> Optional[Path]:
        """Genere un fichier FIT binaire"""
        try:
            import fitdecode
            from fitdecode import FitWriter, Fit

            track_points = fit_data.get('track', {}).get('points', [])
            pois = fit_data.get('pois', [])
            metadata = fit_data.get('metadata', {})

            if not track_points:
                logger.warning("Aucun point de trace pour le fichier FIT")
                return None

            logger.info(f"Generation FIT avec {len(track_points)} points et {len(pois)} POI")

            with FitWriter(str(output_path)) as fit_writer:

                # === FILE_ID ===
                file_id_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['file_id'])
                file_id_frame.set_fields({
                    'type': 4,  # ACTIVITY
                    'manufacturer': 1,  # GARMIN
                    'product': 0,
                    'serial_number': 0,
                    'time_created': int(datetime.now().timestamp())
                })
                fit_writer.write_frame(file_id_frame)

                # === DEVICE_INFO ===
                device_info_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['device_info'])
                device_info_frame.set_fields({
                    'timestamp': int(datetime.now().timestamp()),
                    'manufacturer': 1,
                    'product': 0,
                    'serial_number': 0,
                    'device_index': 0,
                    'source_type': 5,
                    'product_name': 'GPS Analyzer'.encode('ascii')
                })
                fit_writer.write_frame(device_info_frame)

                # === SPORT ===
                sport_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['sport'])
                sport_frame.set_fields({
                    'sport': 0,  # CYCLING
                    'sub_sport': 0
                })
                fit_writer.write_frame(sport_frame)

                # === ACTIVITY (Session) ===
                session_start = datetime.now()
                session_end = session_start + timedelta(seconds=len(track_points) * 2)

                total_dist = metadata.get('total_distance_km', 0) * 1000
                total_ascent = metadata.get('total_ascent_m', 0)

                session_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['session'])
                session_frame.set_fields({
                    'timestamp': int(session_end.timestamp()),
                    'start_time': int(session_start.timestamp()),
                    'total_elapsed_time': len(track_points) * 2,
                    'total_timer_time': len(track_points) * 2,
                    'total_distance': int(total_dist),
                    'total_ascent': int(total_ascent),
                    'sport': 0,
                    'avg_speed': int(total_dist / (len(track_points) * 2) * 3.6) if len(track_points) > 0 else 0,
                    'avg_heart_rate': 0
                })
                fit_writer.write_frame(session_frame)

                # === LAP ===
                lap_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['lap'])
                lap_frame.set_fields({
                    'timestamp': int(session_end.timestamp()),
                    'start_time': int(session_start.timestamp()),
                    'total_elapsed_time': len(track_points) * 2,
                    'total_timer_time': len(track_points) * 2,
                    'total_distance': int(total_dist),
                    'total_ascent': int(total_ascent),
                    'sport': 0
                })
                fit_writer.write_frame(lap_frame)

                # === RECORDS ===
                record_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['record'])
                record_frame.extra_fields.add('position_lat', type='sint32')
                record_frame.extra_fields.add('position_long', type='sint32')
                record_frame.extra_fields.add('altitude', type='uint16')
                record_frame.extra_fields.add('distance', type='uint32')
                record_frame.extra_fields.add('timestamp', type='uint32')

                max_points = min(len(track_points), 10000)

                for i in range(0, max_points, 1):
                    p = track_points[i]
                    
                    lat = int(p.get('latitude', 0) * 11930464.0)
                    lon = int(p.get('longitude', 0) * 11930464.0)
                    alt = int(p.get('elevation', 0) * 5) if p.get('elevation') else 0
                    dist = int(p.get('distance', 0) * 1000)
                    timestamp = int(session_start.timestamp() + (i * 2))

                    record_frame.set_fields({
                        'timestamp': timestamp,
                        'position_lat': lat,
                        'position_long': lon,
                        'altitude': alt,
                        'distance': dist
                    })
                    fit_writer.write_frame(record_frame)

                # === COURSE POINTS (Waypoints POI) ===
                if pois:
                    course_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['course_point'])
                    course_frame.extra_fields.add('position_lat', type='sint32')
                    course_frame.extra_fields.add('position_long', type='sint32')
                    course_frame.extra_fields.add('name', type='string')
                    course_frame.extra_fields.add('timestamp', type='uint32')

                    for poi in pois[:500]:
                        lat = int(poi.get('latitude', 0) * 11930464.0)
                        lon = int(poi.get('longitude', 0) * 11930464.0)
                        name = poi.get('name', 'POI')[:20].encode('ascii', errors='ignore')

                        course_frame.set_fields({
                            'timestamp': int(session_end.timestamp()),
                            'position_lat': lat,
                            'position_long': lon,
                            'name': name
                        })
                        fit_writer.write_frame(course_frame)

                # === EVENT ===
                event_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['event'])
                event_frame.set_fields({
                    'timestamp': int(session_end.timestamp()),
                    'event': 3,
                    'event_group': 0,
                    'event_type': 1,
                    'data': 0,
                    'data16': 0
                })
                fit_writer.write_frame(event_frame)

                # === ACTIVITY ===
                activity_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['activity'])
                activity_frame.set_fields({
                    'timestamp': int(session_end.timestamp()),
                    'total_timer_time': len(track_points) * 2,
                    'num_sessions': 1,
                    'type': 1,
                    'event': 0,
                    'event_type': 0,
                    'local_timestamp': int(session_end.timestamp())
                })
                fit_writer.write_frame(activity_frame)

            logger.info(f"Fichier FIT genere: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Erreur generation FIT: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None