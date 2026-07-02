#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import gpxpy
import gpxpy.gpx
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class FileConverter:
    """Convertisseur de fichiers GPS (KML, TCX, FIT -> GPX)"""

    @staticmethod
    def convert_to_gpx(input_file: Path, output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Convertit un fichier KML, TCX ou FIT en GPX
        
        Args:
            input_file: Fichier source (.kml, .tcx, .fit)
            output_dir: Répertoire de sortie (optionnel)
            
        Returns:
            Chemin du fichier GPX converti
        """
        if not input_file.exists():
            logger.error(f"Fichier introuvable: {input_file}")
            return None
        
        suffix = input_file.suffix.lower()
        
        if suffix == '.gpx':
            logger.info(f"Fichier deja en GPX: {input_file}")
            return input_file
        
        if output_dir is None:
            output_dir = input_file.parent
        
        output_file = output_dir / f"{input_file.stem}.gpx"
        
        if suffix == '.kml':
            return FileConverter._kml_to_gpx(input_file, output_file)
        elif suffix == '.tcx':
            return FileConverter._tcx_to_gpx(input_file, output_file)
        elif suffix == '.fit':
            return FileConverter._fit_to_gpx(input_file, output_file)
        else:
            logger.error(f"Format non supporte: {suffix}")
            return None

    @staticmethod
    def _kml_to_gpx(kml_file: Path, output_file: Path) -> Optional[Path]:
        """Convertit un fichier KML en GPX"""
        try:
            tree = ET.parse(kml_file)
            root = tree.getroot()
            
            # Namespace KML
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            gpx = gpxpy.gpx.GPX()
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            
            # Extraire les coordonnees des placemarks
            for placemark in root.findall('.//kml:Placemark', ns):
                for line_string in placemark.findall('.//kml:LineString', ns):
                    coords_text = line_string.find('kml:coordinates', ns)
                    if coords_text is not None and coords_text.text:
                        for coord in coords_text.text.strip().split():
                            parts = coord.split(',')
                            if len(parts) >= 2:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                elev = float(parts[2]) if len(parts) > 2 else None
                                point = gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=elev)
                                gpx_segment.points.append(point)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"KML -> GPX: {output_file} ({len(gpx_segment.points)} points)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur conversion KML->GPX: {e}")
            return None

    @staticmethod
    def _tcx_to_gpx(tcx_file: Path, output_file: Path) -> Optional[Path]:
        """Convertit un fichier TCX en GPX"""
        try:
            tree = ET.parse(tcx_file)
            root = tree.getroot()
            
            # Namespace TCX
            ns = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
            
            gpx = gpxpy.gpx.GPX()
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            
            # Extraire les points de track
            for trackpoint in root.findall('.//tcx:Trackpoint', ns):
                lat = None
                lon = None
                elev = None
                time = None
                
                pos = trackpoint.find('tcx:Position', ns)
                if pos is not None:
                    lat_elem = pos.find('tcx:LatitudeDegrees', ns)
                    lon_elem = pos.find('tcx:LongitudeDegrees', ns)
                    if lat_elem is not None:
                        lat = float(lat_elem.text)
                    if lon_elem is not None:
                        lon = float(lon_elem.text)
                
                alt_elem = trackpoint.find('tcx:AltitudeMeters', ns)
                if alt_elem is not None:
                    elev = float(alt_elem.text)
                
                time_elem = trackpoint.find('tcx:Time', ns)
                if time_elem is not None:
                    try:
                        time = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
                    except:
                        pass
                
                if lat is not None and lon is not None:
                    point = gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=elev, time=time)
                    gpx_segment.points.append(point)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"TCX -> GPX: {output_file} ({len(gpx_segment.points)} points)")
            return output_file
            
        except Exception as e:
            logger.error(f"Erreur conversion TCX->GPX: {e}")
            return None

    @staticmethod
    def _fit_to_gpx(fit_file: Path, output_file: Path) -> Optional[Path]:
        """Convertit un fichier FIT en GPX"""
        try:
            # Essayer avec fitdecode
            try:
                import fitdecode
                
                gpx = gpxpy.gpx.GPX()
                gpx_track = gpxpy.gpx.GPXTrack()
                gpx.tracks.append(gpx_track)
                
                gpx_segment = gpxpy.gpx.GPXTrackSegment()
                gpx_track.segments.append(gpx_segment)
                
                with fitdecode.FitFile(str(fit_file)) as fit:
                    for frame in fit:
                        if isinstance(frame, fitdecode.records.RecordDataMessage):
                            lat = frame.get_value('position_lat')
                            lon = frame.get_value('position_long')
                            alt = frame.get_value('altitude')
                            timestamp = frame.get_value('timestamp')
                            
                            if lat is not None and lon is not None:
                                lat_deg = lat / 11930464.0
                                lon_deg = lon / 11930464.0
                                point = gpxpy.gpx.GPXTrackPoint(lat_deg, lon_deg, elevation=alt, time=timestamp)
                                gpx_segment.points.append(point)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(gpx.to_xml())
                
                logger.info(f"FIT -> GPX: {output_file} ({len(gpx_segment.points)} points)")
                return output_file
                
            except ImportError:
                logger.error("fitdecode non disponible pour convertir FIT en GPX")
                return None
                
        except Exception as e:
            logger.error(f"Erreur conversion FIT->GPX: {e}")
            return None

    @staticmethod
    def get_file_type(file_path: Path) -> str:
        """Retourne le type du fichier (gpx, kml, tcx, fit)"""
        suffix = file_path.suffix.lower()
        if suffix in ['.gpx', '.kml', '.tcx', '.fit']:
            return suffix[1:]
        return 'unknown'