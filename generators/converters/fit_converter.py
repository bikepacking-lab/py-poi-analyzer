#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime
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


class FITConverter(BaseGenerator):
    """Convertisseur FIT sans POI"""

    def get_format_type(self) -> str:
        return 'fit'

    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[List[Path]]:
        """Génère un FIT sans POI"""

        try:
            track_points = data.get('track_points', [])
            
            if not track_points:
                logger.warning("Aucun point de trace pour le FIT")
                return None

            # Générer le JSON (OBLIGATOIRE)
            analysis_id = data.get('analysis_id', 'unknown')
            json_file = output_dir / f"converted_track_{analysis_id}.json"
            
            fit_data = self._prepare_fit_data(data)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(fit_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Donnees FIT JSON generees: {json_file}")
            
            # Générer le FIT si disponible
            if FIT_AVAILABLE:
                fit_file = output_dir / f"converted_track_{analysis_id}.fit"
                fit_path = None
                
                # Essayer avec fitdecode d'abord
                if FITDECODE_AVAILABLE:
                    try:
                        logger.info("Tentative generation FIT avec fitdecode...")
                        fit_path = self._generate_fit_with_fitdecode(fit_data, fit_file)
                        if fit_path and fit_path.exists():
                            logger.info(f"FIT genere avec fitdecode: {fit_path}")
                            return [json_file, fit_path]
                    except Exception as e:
                        logger.warning(f"Generation FIT avec fitdecode echouee: {e}")
                
                # Si fitdecode a echoue, essayer avec fit-tools
                if FITTOOLS_AVAILABLE and not (fit_path and fit_path.exists()):
                    try:
                        logger.info("Tentative generation FIT avec fit-tools...")
                        fit_path = self._generate_fit_with_fittools(fit_data, fit_file)
                        if fit_path and fit_path.exists():
                            logger.info(f"FIT genere avec fit-tools: {fit_path}")
                            return [json_file, fit_path]
                    except Exception as e:
                        logger.warning(f"Generation FIT avec fit-tools echouee: {e}")
                
                # Si les deux ont echoue
                if not (fit_path and fit_path.exists()):
                    logger.warning("Generation FIT a echoue avec les deux bibliotheques")
                    return [json_file]
            else:
                logger.warning("Aucune bibliotheque FIT disponible")
                logger.info("Installez: pip install fit-tool")
                return [json_file]
            
        except Exception as e:
            logger.error(f"Erreur FIT: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _prepare_fit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare les donnees FIT"""
        track_points = data.get('track_points', [])
        summary = data.get('summary', {})
        track_info = summary.get('track_info', {})

        return {
            'metadata': {
                'version': '1.0',
                'generated': datetime.now().isoformat(),
                'analysis_id': data.get('analysis_id', ''),
                'total_distance_km': track_info.get('total_distance_km', 0),
                'total_ascent_m': track_info.get('total_ascent_m', 0),
                'total_descent_m': track_info.get('total_descent_m', 0)
            },
            'track': {
                'points': [
                    {
                        'latitude': p.get('latitude', 0),
                        'longitude': p.get('longitude', 0),
                        'elevation': p.get('elevation', 0),
                        'distance': p.get('distance', 0)
                    }
                    for p in track_points
                ]
            }
        }

    def _generate_fit_with_fitdecode(self, fit_data: Dict[str, Any], output_path: Path) -> Optional[Path]:
        """Genere un fichier FIT avec fitdecode"""
        try:
            from fitdecode import FitWriter, Fit

            track_points = fit_data.get('track', {}).get('points', [])
            metadata = fit_data.get('metadata', {})

            if not track_points:
                return None

            logger.info(f"Generation FIT (fitdecode): {len(track_points)} points")

            with FitWriter(str(output_path)) as fit_writer:
                # FILE_ID
                file_id_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['file_id'])
                file_id_frame.set_fields({
                    'type': 4,
                    'manufacturer': 1,
                    'time_created': int(datetime.now().timestamp())
                })
                fit_writer.write_frame(file_id_frame)

                # RECORDS
                record_frame = fit_writer.create_definition_frame(Fit.FIELD_DEFINITIONS['record'])
                record_frame.extra_fields.add('position_lat', type='sint32')
                record_frame.extra_fields.add('position_long', type='sint32')
                record_frame.extra_fields.add('altitude', type='uint16')
                record_frame.extra_fields.add('distance', type='uint32')
                record_frame.extra_fields.add('timestamp', type='uint32')

                session_start = datetime.now()

                for i, p in enumerate(track_points[:10000]):
                    lat = int(p.get('latitude', 0) * 11930464.0)
                    lon = int(p.get('longitude', 0) * 11930464.0)
                    alt = int(p.get('elevation', 0) * 5) if p.get('elevation') else 0
                    dist = int(p.get('distance', 0) * 1000)

                    record_frame.set_fields({
                        'timestamp': int(session_start.timestamp() + (i * 2)),
                        'position_lat': lat,
                        'position_long': lon,
                        'altitude': alt,
                        'distance': dist
                    })
                    fit_writer.write_frame(record_frame)

            return output_path

        except Exception as e:
            logger.error(f"Erreur generation FIT avec fitdecode: {e}")
            raise

    def _generate_fit_with_fittools(self, fit_data: Dict[str, Any], output_path: Path) -> Optional[Path]:
        """Genere un fichier FIT avec fit-tool (paquet PyPI: fit-tool, module: fit_tool)"""
        try:
            from fit_tool.fit_file_builder import FitFileBuilder
            from fit_tool.profile.messages.file_id_message import FileIdMessage
            from fit_tool.profile.messages.record_message import RecordMessage
            from fit_tool.profile.messages.session_message import SessionMessage
            from fit_tool.profile.messages.lap_message import LapMessage
            from fit_tool.profile.messages.event_message import EventMessage
            from fit_tool.profile.messages.activity_message import ActivityMessage
            from fit_tool.profile.profile_type import FileType, Manufacturer, Sport, Event, EventType

            track_points = fit_data.get('track', {}).get('points', [])
            metadata = fit_data.get('metadata', {})

            if not track_points:
                return None

            logger.info(f"Generation FIT (fit-tool): {len(track_points)} points")

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

            n_points = min(len(track_points), 10000)
            session_start_dt = datetime.now()
            session_start_ms = now_ms
            elapsed_s = max(n_points * 2, 1)
            session_end_ms = session_start_ms + elapsed_s * 1000

            total_dist_m = float(metadata.get('total_distance_km', 0) or 0) * 1000
            total_ascent_m = float(metadata.get('total_ascent_m', 0) or 0)
            total_descent_m = float(metadata.get('total_descent_m', 0) or 0)

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
            logger.error(f"Erreur generation FIT avec fit-tool: {e}")
            raise