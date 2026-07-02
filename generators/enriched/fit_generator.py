#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime, timedelta

from ..base_generator import BaseGenerator

logger = logging.getLogger(__name__)

# === TENTATIVE D'IMPORT FITDECODE ===
FITDECODE_AVAILABLE = False
try:
    import fitdecode
    from fitdecode import FitWriter, Fit
    FITDECODE_AVAILABLE = True
    logger.info("fitdecode disponible")
except ImportError:
    logger.debug("fitdecode non disponible")
except Exception as e:
    logger.debug(f"Erreur import fitdecode: {e}")

# === TENTATIVE D'IMPORT FIT-TOOL (paquet PyPI: fit-tool, module: fit_tool) ===
FITTOOLS_AVAILABLE = False
try:
    from fit_tool.fit_file_builder import FitFileBuilder
    FITTOOLS_AVAILABLE = True
    logger.info("fit-tool disponible")
except ImportError:
    logger.debug("fit-tool non disponible")
except Exception as e:
    logger.debug(f"Erreur import fit-tool: {e}")

FIT_AVAILABLE = FITDECODE_AVAILABLE or FITTOOLS_AVAILABLE


class FITGenerator(BaseGenerator):
    """Générateur de fichiers FIT enrichis avec POI"""

    def get_format_type(self) -> str:
        return 'fit-enriched'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[List[Path]]:
        """Génère un fichier FIT enrichi et un JSON de données"""

        output_file = output_dir / f'enriched_track_{data.get("analysis_id", "unknown")}.json'
        fit_file = output_dir / f'enriched_track_{data.get("analysis_id", "unknown")}.fit'

        try:
            # 1. Préparer les données
            fit_data = self._prepare_fit_data(data)

            # 2. Sauvegarder en JSON (OBLIGATOIRE)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fit_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Donnees FIT enrichi JSON generees: {output_file}")

            # 3. Générer le fichier FIT binaire
            if FIT_AVAILABLE:
                fit_path = None
                
                # Essayer avec fitdecode d'abord
                if FITDECODE_AVAILABLE:
                    try:
                        logger.info("Tentative generation FIT enrichi avec fitdecode...")
                        fit_path = self._generate_fit_with_fitdecode(fit_data, fit_file, data)
                        if fit_path and fit_path.exists():
                            logger.info(f"FIT enrichi genere avec fitdecode: {fit_path}")
                            return [output_file, fit_path]
                    except Exception as e:
                        logger.warning(f"Generation FIT enrichi avec fitdecode echouee: {e}")
                
                # Si fitdecode a echoue, essayer avec fit-tools
                if FITTOOLS_AVAILABLE and not (fit_path and fit_path.exists()):
                    try:
                        logger.info("Tentative generation FIT enrichi avec fit-tools...")
                        fit_path = self._generate_fit_with_fittools(fit_data, fit_file, data)
                        if fit_path and fit_path.exists():
                            logger.info(f"FIT enrichi genere avec fit-tools: {fit_path}")
                            return [output_file, fit_path]
                    except Exception as e:
                        logger.warning(f"Generation FIT enrichi avec fit-tools echouee: {e}")
                
                # Si les deux ont echoue
                if not (fit_path and fit_path.exists()):
                    logger.warning("Generation FIT enrichi a echoue avec les deux bibliotheques")
                    return [output_file]
            else:
                logger.warning("Aucune bibliotheque FIT disponible")
                logger.info("Installez: pip install fit-tool")
                logger.info("Le fichier JSON a ete genere")
                return [output_file]

        except Exception as e:
            logger.error(f"Erreur FIT enrichi: {e}")
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

    def _generate_fit_with_fitdecode(self, fit_data: Dict[str, Any], output_path: Path, data: Dict[str, Any]) -> Optional[Path]:
        """Genere un fichier FIT enrichi avec fitdecode"""
        try:
            from fitdecode import FitWriter, Fit

            track_points = fit_data.get('track', {}).get('points', [])
            pois = fit_data.get('pois', [])
            metadata = fit_data.get('metadata', {})

            if not track_points:
                logger.warning("Aucun point de trace pour le FIT")
                return None

            logger.info(f"Generation FIT enrichi (fitdecode): {len(track_points)} points, {len(pois)} POI")

            with FitWriter(str(output_path)) as fit_writer:

                # FILE_ID
                file_id_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['file_id'])
                file_id_frame.set_fields({
                    'type': 4,
                    'manufacturer': 1,
                    'product': 0,
                    'serial_number': 0,
                    'time_created': int(datetime.now().timestamp())
                })
                fit_writer.write_frame(file_id_frame)

                # DEVICE_INFO
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

                # SPORT
                sport_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['sport'])
                sport_frame.set_fields({
                    'sport': 0,
                    'sub_sport': 0
                })
                fit_writer.write_frame(sport_frame)

                # SESSION
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
                    'avg_speed': int(total_dist / (len(track_points) * 2) * 3.6) if len(track_points) > 0 else 0
                })
                fit_writer.write_frame(session_frame)

                # LAP
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

                # RECORDS
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

                # COURSE POINTS (POI)
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

                # EVENT
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

                # ACTIVITY
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

            return output_path

        except Exception as e:
            logger.error(f"Erreur generation FIT enrichi avec fitdecode: {e}")
            raise

    def _generate_fit_with_fittools(self, fit_data: Dict[str, Any], output_path: Path, data: Dict[str, Any]) -> Optional[Path]:
        """Genere un fichier FIT enrichi avec fit-tool (paquet PyPI: fit-tool, module: fit_tool)"""
        try:
            from fit_tool.fit_file_builder import FitFileBuilder
            from fit_tool.profile.messages.file_id_message import FileIdMessage
            from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
            from fit_tool.profile.messages.record_message import RecordMessage
            from fit_tool.profile.messages.session_message import SessionMessage
            from fit_tool.profile.messages.lap_message import LapMessage
            from fit_tool.profile.messages.course_point_message import CoursePointMessage
            from fit_tool.profile.messages.event_message import EventMessage
            from fit_tool.profile.messages.activity_message import ActivityMessage
            from fit_tool.profile.profile_type import (
                FileType, Manufacturer, Sport, Event, EventType, CoursePoint,
            )

            track_points = fit_data.get('track', {}).get('points', [])
            pois = fit_data.get('pois', [])
            metadata = fit_data.get('metadata', {})

            if not track_points:
                logger.warning("Aucun point de trace pour le FIT")
                return None

            logger.info(f"Generation FIT enrichi (fit-tool): {len(track_points)} points, {len(pois)} POI")

            # NB: dans fit-tool, les champs prennent des valeurs "semantiques"
            # directement (degres decimaux pour lat/lon, metres pour altitude/
            # distance, millisecondes epoch pour les timestamps) : la
            # conversion vers le format binaire FIT (semicircles, scale/offset...)
            # est geree en interne par la librairie.

            builder = FitFileBuilder(auto_define=True, min_string_size=50)

            now_ms = int(datetime.now().timestamp() * 1000)

            # FILE_ID (obligatoire, doit etre le premier message)
            file_id = FileIdMessage()
            file_id.type = FileType.ACTIVITY
            file_id.manufacturer = Manufacturer.DEVELOPMENT.value
            file_id.product = 0
            file_id.time_created = now_ms
            file_id.serial_number = 0x12345678
            builder.add(file_id)

            # DEVICE_INFO
            device_info = DeviceInfoMessage()
            device_info.timestamp = now_ms
            device_info.manufacturer = Manufacturer.DEVELOPMENT.value
            device_info.product = 0
            device_info.device_index = 0
            device_info.source_type = 5  # LOCAL
            device_info.product_name = "GPS Analyzer"
            builder.add(device_info)

            # Horodatage synthetique (pas de temps reel dans les points) :
            # un point toutes les 2 secondes a partir de maintenant
            session_start_dt = datetime.now()
            n_points = min(len(track_points), 10000)
            session_end_dt = session_start_dt + timedelta(seconds=n_points * 2)
            session_start_ms = int(session_start_dt.timestamp() * 1000)
            session_end_ms = int(session_end_dt.timestamp() * 1000)

            total_dist_m = float(metadata.get('total_distance_km', 0) or 0) * 1000
            total_ascent_m = float(metadata.get('total_ascent_m', 0) or 0)
            total_descent_m = float(metadata.get('total_descent_m', 0) or 0)
            elapsed_s = max(n_points * 2, 1)

            # EVENT (start)
            event_start = EventMessage()
            event_start.timestamp = session_start_ms
            event_start.event = Event.TIMER
            event_start.event_type = EventType.START
            builder.add(event_start)

            # RECORDS
            first_lat = first_lon = None
            last_lat = last_lon = None
            for i in range(n_points):
                p = track_points[i]
                record = RecordMessage()
                record.timestamp = session_start_ms + i * 2000

                lat = p.get('latitude')
                lon = p.get('longitude')
                if lat is not None:
                    record.position_lat = float(lat)
                if lon is not None:
                    record.position_long = float(lon)
                if p.get('elevation') is not None:
                    record.altitude = float(p.get('elevation') or 0)
                if p.get('distance') is not None:
                    record.distance = float(p.get('distance') or 0) * 1000  # km -> m

                builder.add(record)

                if first_lat is None and lat is not None and lon is not None:
                    first_lat, first_lon = float(lat), float(lon)
                if lat is not None and lon is not None:
                    last_lat, last_lon = float(lat), float(lon)

            # COURSE POINTS (POI)
            for poi in pois[:500]:
                cp = CoursePointMessage()
                cp.timestamp = session_end_ms
                lat = poi.get('latitude')
                lon = poi.get('longitude')
                if lat is not None:
                    cp.position_lat = float(lat)
                if lon is not None:
                    cp.position_long = float(lon)
                cp.course_point_name = (poi.get('name') or 'POI')[:20]
                cp.type = CoursePoint.GENERIC
                builder.add(cp)

            # EVENT (stop)
            event_stop = EventMessage()
            event_stop.timestamp = session_end_ms
            event_stop.event = Event.TIMER
            event_stop.event_type = EventType.STOP_ALL
            builder.add(event_stop)

            # LAP
            lap = LapMessage()
            lap.timestamp = session_end_ms
            lap.start_time = session_start_ms
            lap.total_elapsed_time = elapsed_s
            lap.total_timer_time = elapsed_s
            lap.total_distance = total_dist_m
            lap.total_ascent = total_ascent_m
            lap.total_descent = total_descent_m
            lap.sport = Sport.GENERIC
            if first_lat is not None:
                lap.start_position_lat = first_lat
                lap.start_position_long = first_lon
            if last_lat is not None:
                lap.end_position_lat = last_lat
                lap.end_position_long = last_lon
            builder.add(lap)

            # SESSION
            session = SessionMessage()
            session.timestamp = session_end_ms
            session.start_time = session_start_ms
            session.total_elapsed_time = elapsed_s
            session.total_timer_time = elapsed_s
            session.total_distance = total_dist_m
            session.total_ascent = total_ascent_m
            session.total_descent = total_descent_m
            session.sport = Sport.GENERIC
            session.first_lap_index = 0
            session.num_laps = 1
            session.avg_speed = (total_dist_m / elapsed_s) if elapsed_s else 0
            if first_lat is not None:
                session.start_position_lat = first_lat
                session.start_position_long = first_lon
            builder.add(session)

            # ACTIVITY (doit etre le dernier message)
            activity = ActivityMessage()
            activity.timestamp = session_end_ms
            activity.total_timer_time = elapsed_s
            activity.num_sessions = 1
            activity.type = 0  # manual
            activity.event = Event.ACTIVITY
            activity.event_type = EventType.STOP
            # local_timestamp est un champ brut (secondes, epoch FIT local) et
            # non un TimestampField : on ne le renseigne pas, il est optionnel.
            builder.add(activity)

            fit_file = builder.build()
            fit_file.to_file(str(output_path))

            return output_path

        except Exception as e:
            logger.error(f"Erreur generation FIT enrichi avec fit-tool: {e}")
            raise