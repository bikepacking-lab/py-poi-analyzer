#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from dataclasses import dataclass, asdict
import math
import re
import threading
import hashlib
from config import (
    AVAILABLE_POI_TAGS_OSM, POI_API_URL, 
    OVERPASS_DEBUG_MODE, MAX_TAGS_PER_TYPE
)
        
logger = logging.getLogger(__name__)

@dataclass
class POI:
    """Point d'Interet - Version enrichie"""
    id: str
    type: str
    lat: float
    lon: float
    name: Optional[str]
    tags: Dict[str, Any]
    distance: Optional[float] = None
    distance_along_track: Optional[float] = None
    osm_type: str = 'node'
    
    # Informations enrichies
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    google_maps_url: Optional[str] = None
    overpass_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire avec toutes les informations"""
        return {
            'id': self.id,
            'type': self.type,
            'lat': self.lat,
            'lon': self.lon,
            'name': self.name,
            'tags': self.tags,
            'distance': self.distance,
            'distance_along_track': self.distance_along_track,
            'osm_type': self.osm_type,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'opening_hours': self.opening_hours,
            'description': self.description,
            'google_maps_url': self.google_maps_url,
            'overpass_url': self.overpass_url
        }

class RateLimiter:
    """Rate limiting thread-safe - Plus strict"""
    
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval = 60.0 / max_requests_per_minute
        self.lock = threading.Lock()
        self.last_request_time = 0.0
    
    def wait(self):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: attente {wait_time:.1f}s")
                time.sleep(wait_time)
            self.last_request_time = time.time()

class POIDetector:
    """Detecteur de Points d'Interet - Version optimisee"""
    
    def __init__(self, cache_manager=None):
        self.cache = cache_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GPS-POI-Analyzer/1.0',
            'Accept': 'application/json'
        })
        # Rate limiting strict: 10 requetes par minute
        self.rate_limiter = RateLimiter(max_requests_per_minute=10)
        self.max_retries = 5
        self.retry_delays = [10, 20, 30, 45, 60]
        self.timeout = 120
        self.query_cache = {}
        self.cache_lock = threading.Lock()
        logger.info("POIDetector initialise (rate limit: 10 req/min)")
    
    def _build_overpass_query(self, bbox: Tuple[float, float, float, float], 
                             poi_types: List[str], 
                             tags_config: Dict,
                             max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> str:
        """Construit une requete Overpass"""
        lat_min, lon_min, lat_max, lon_max = bbox
        bbox_str = f"{lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}"
        
        queries = []

        logger.info(f"=== CONSTRUCTION REQUETE OVERPASS ===")
        logger.info(f"Bbox: {bbox_str}")
        logger.info(f"Types: {poi_types}")
        logger.info(f"max_tags_per_type: {max_tags_per_type}")
    
        for poi_type in poi_types:
            if poi_type not in tags_config:
                continue
            
            tags_list = tags_config[poi_type]
        
            if max_tags_per_type and max_tags_per_type > 0:
                tags_list = tags_list[:max_tags_per_type]
                
            logger.info(f"Type '{poi_type}' - {len(tags_list)} tags disponibles")
            
            selected_tags = tags_list[:max_tags_per_type]
            logger.info(f"  Tags utilises ({len(selected_tags)}):")
            logger.info(f"  Tags utilises ({len(selected_tags)}):")
            for i, tag in enumerate(selected_tags):
                logger.info(f"    {i+1}. {tag}")
            
            for tag_filter in tags_list:
                tag_clean = tag_filter.strip()
                queries.append(f'node{tag_clean}({bbox_str});')
                queries.append(f'way{tag_clean}({bbox_str});')
                queries.append(f'relation{tag_clean}({bbox_str});')
                
        if not queries:
            return ''
        
        # Requete avec timeout court pour Overpass
        query = '[out:json][timeout:25];\n(\n'
        query += '\n'.join(queries)
        query += '\n);\nout body qt;'
        
        logger.info(f"Requete construite ({len(queries)} sous-requetes)")
        logger.debug(f"Requete complete: {query[:500]}...")

        return query
    
    def _query_overpass(self, query: str) -> Optional[List[Dict]]:
        """Execute une requete Overpass avec retry et backoff"""
        
        #! Force le vidate du cache
        # self.query_cache.clear()
        
        # Cache memoire
        query_hash = hashlib.md5(query.encode()).hexdigest()
        with self.cache_lock:
            if query_hash in self.query_cache:
                cache_time, cache_data = self.query_cache[query_hash]
                if (time.time() - cache_time) < 600:  # 10 minutes
                    logger.debug(f"Cache memoire hit: {query_hash[:8]}")
                    return cache_data
        
        if OVERPASS_DEBUG_MODE:
            logger.debug(f"Requete Overpass: {query[:80]}...")
        
        for attempt in range(self.max_retries):
            try:
                self.rate_limiter.wait()
                
                response = self.session.post(
                    POI_API_URL,
                    data={'data': query},
                    timeout=self.timeout,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        elements = data.get('elements', [])
                        if not elements:
                            return []
                        
                        valid = []
                        for e in elements:
                            if self._validate_element(e):
                                valid.append(e)
                        
                        with self.cache_lock:
                            self.query_cache[query_hash] = (time.time(), valid)
                        
                        logger.debug(f"Requete OK: {len(valid)} elements")
                        return valid
                    except json.JSONDecodeError:
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delays[attempt])
                        continue
                
                elif response.status_code == 504:
                    wait = self.retry_delays[attempt] + 10
                    logger.warning(f"Gateway Timeout 504, attente {wait}s ({attempt+1}/{self.max_retries})")
                    time.sleep(wait)
                    continue
                    
                elif response.status_code == 429:
                    wait = self.retry_delays[attempt] * 3
                    logger.warning(f"Rate limit 429, attente {wait}s")
                    time.sleep(wait)
                    continue
                    
                elif response.status_code == 400:
                    logger.error(f"Bad Request: {response.text[:200]}")
                    return None
                    
                elif response.status_code in [500, 502, 503]:
                    wait = self.retry_delays[attempt]
                    logger.warning(f"Erreur serveur {response.status_code}, attente {wait}s")
                    time.sleep(wait)
                    continue
                    
                else:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delays[attempt])
                    continue
                
            except requests.Timeout:
                logger.warning(f"Timeout ({attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delays[attempt] + 5)
                continue
            except Exception as e:
                logger.error(f"Erreur: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delays[attempt])
                continue
        
        logger.error(f"Echec apres {self.max_retries} tentatives")
        return None
    
    def _validate_element(self, element: Dict) -> bool:
        """Valide un element Overpass"""
        if element.get('type') == 'node':
            if 'lat' not in element or 'lon' not in element:
                return False
            if not (-90.0 <= element['lat'] <= 90.0) or not (-180.0 <= element['lon'] <= 180.0):
                return False
            return True
        return False
    
    def _process_result(self, elements: List[Dict], poi_type: str) -> List[POI]:
        """Traite les resultats Overpass avec filtrage des POI vides"""
        pois = []
        
        logger.info(f"Traitement des resultats pour '{poi_type}' - {len(elements)} elements")
        
        for element in elements:
            try:
                tags = element.get('tags', {})
                
                # DEBUG: Afficher les tags des elements rejetes
                if poi_type == 'bivouac':
                    logger.debug(f"Element tags: {tags}")
                
                if not self._match_type(tags, poi_type):
                    if poi_type == 'bivouac':
                        logger.debug(f"  Rejete - ne correspond pas au type")
                    
                    continue
            
                lat = element.get('lat', 0.0)
                lon = element.get('lon', 0.0)
            
                # FILTRAGE: Ignorer les POI sans coordonnees valides
                if lat == 0.0 and lon == 0.0:
                    continue
                if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                    continue
            
                # FILTRAGE: Ignorer les POI sans nom ET sans tags utiles
                name = tags.get('name') or tags.get('ref')
                if not name and not tags:
                    continue
            
                # FILTRAGE: Ignorer les POI avec seulement des tags generiques
                if not name and len(tags) < 2:
                    continue
            
                poi = POI(
                    id=f"node_{element.get('id', '')}",
                    type=poi_type,
                    lat=lat,
                    lon=lon,
                    name=name,
                    tags=tags,
                    osm_type='node'
                )
            
                # Enrichissement
                poi.address = self._build_address(tags)
                poi.phone = tags.get('phone') or tags.get('contact:phone')
                poi.website = tags.get('website') or tags.get('url') or tags.get('contact:website')
                poi.opening_hours = tags.get('opening_hours')
                poi.description = tags.get('description') or tags.get('note')
                poi.google_maps_url = f"https://www.google.com/maps/place/{lat},{lon}"
                poi.overpass_url = f"https://overpass-turbo.eu/?Q=node({element.get('id', '')});out+body;&R"
            
                pois.append(poi)
            except Exception:
                continue
            
        logger.info(f"Resultat pour '{poi_type}': {len(pois)} POI")
        return pois
    
    def _build_address(self, tags: Dict) -> Optional[str]:
        """Construit une adresse à partir des tags"""
        address_parts = []
        
        # Tags d'adresse courants
        addr_fields = [
            ('addr:housenumber', ''),
            ('addr:street', ''),
            ('addr:place', ''),
            ('addr:city', ''),
            ('addr:postcode', ''),
            ('addr:country', '')
        ]
        
        for field, _ in addr_fields:
            value = tags.get(field)
            if value:
                address_parts.append(value)
        
        # Si pas d'adresse structurée, essayer des champs alternatifs
        if not address_parts:
            alt_fields = ['address', 'location', 'place']
            for field in alt_fields:
                value = tags.get(field)
                if value:
                    address_parts.append(value)
                    break
        
        return ', '.join(address_parts) if address_parts else None

    
    def _match_type(self, tags: Dict, poi_type: str) -> bool:
        """Verifie si les tags correspondent au type"""
    
        if poi_type not in AVAILABLE_POI_TAGS_OSM:
            return True
    
        filters = AVAILABLE_POI_TAGS_OSM[poi_type]
    
        for filter_str in filters:
            if self._match_filter_permissive(tags, filter_str):
                return True
    
        return False

    def _match_filter_permissive(self, tags: Dict, filter_str: str) -> bool:
        """Verifie si les tags correspondent a un filtre"""
        try:
            pattern = r'\["([^"]+)"\s*([=!~]=?|~)\s*"([^"]*)"\]'
            conditions = re.findall(pattern, filter_str)
        
            if not conditions: return False
        
            matched = 0
            total = len(conditions)
        
            for key, operator, value in conditions:
                if key not in tags:
                    continue
            
                tag_value = str(tags[key])
            
                if operator == '=':
                    if tag_value == value:
                        matched += 1
                elif operator == '!=':
                    if tag_value != value:
                        matched += 1
                elif operator == '~':
                    if re.search(value, tag_value):
                        matched += 1
                elif operator == '!~':
                    if not re.search(value, tag_value):
                        matched += 1
        
            if total == 1: return matched >= 1
            else: return matched >= total / 2
        except Exception:
            return False
    
    def _match_filter(self, tags: Dict, filter_str: str) -> bool:
        """Verifie si les tags correspondent a un filtre"""
        try:
            pattern = r'\["([^"]+)"\s*([=!~]=?|~)\s*"([^"]*)"\]'
            conditions = re.findall(pattern, filter_str)
            
            if not conditions:
                return False
            
            for key, operator, value in conditions:
                if key not in tags:
                    return False
                tag_value = str(tags[key])
                
                if operator == '=':
                    if tag_value != value:
                        return False
                elif operator == '!=':
                    if tag_value == value:
                        return False
                elif operator == '~':
                    if not re.search(value, tag_value):
                        return False
            return True
        except Exception:
            return False
    
    def _extract_from_bbox(self, bbox: Tuple[float, float, float, float], 
                          poi_types: List[str], 
                          tags_config: Dict,
                          radius: float,
                          max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> List[POI]:
        """Extrait les POI d'une bbox avec cache"""
        if not bbox or not poi_types:
            return []
        
        # Cache Redis
        cache_key = f"poi:{bbox}:{','.join(sorted(poi_types))}:{max_tags_per_type}"
        cached = self.cache.get(cache_key) if self.cache else None
        if cached:
            logger.debug(f"Cache Redis hit")
            return [POI(**p) for p in cached]
        
        query = self._build_overpass_query(bbox, poi_types, tags_config, max_tags_per_type)
        if not query:
            return []
        
        elements = self._query_overpass(query)
        if not elements:
            return []
        
        all_pois = []
        for poi_type in poi_types:
            all_pois.extend(self._process_result(elements, poi_type))
        
        # Filtrage par distance
        if radius > 0.0 and all_pois:
            center_lat = (bbox[0] + bbox[2]) / 2.0
            center_lon = (bbox[1] + bbox[3]) / 2.0
            filtered = []
            for poi in all_pois:
                dist = self._haversine_distance(poi.lat, poi.lon, center_lat, center_lon)
                if dist <= radius / 1000.0:
                    filtered.append(poi)
                    all_pois = filtered
        
        # Cache Redis
        if self.cache and all_pois:
            try:
                self.cache.set(cache_key, [p.to_dict() for p in all_pois], ttl=86400)
            except Exception:
                pass
        
        return all_pois
    
    def detect_pois(self, 
                   bboxes: List[Tuple[float, float, float, float]], 
                   poi_types: List[str],
                   tags_config: Dict,
                   radii: Dict[str, float],
                   max_workers: int = 1,
                   max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> List[POI]:
        """
        Detecte les POI - MODE SERIE OBLIGATOIRE
        
        Args:
            bboxes: Liste des bboxes
            poi_types: Types de POI a rechercher
            tags_config: Configuration des tags OSM
            radii: Dict[str, float] - Rayons par type (en metres)
            max_workers: Force a 1 (mode serie)
            max_tags_per_type: Nombre max de tags par type (le nombre peut ralentir la recherche)
        """
        if not bboxes or not poi_types:
            return []
        
        # FORCER LE MODE SERIE pour eviter les timeouts
        effective_workers = 1
        logger.info(f"Detection POI: {len(bboxes)} bboxes (mode serie obligatoire)")
        
        all_pois = []
        seen = set()
        max_radius = max(radii.values()) if radii else 0.0
        
        # Traitement SERIE un par un avec pauses
        for i, bbox in enumerate(bboxes):
            try:
                logger.info(f"Bbox {i+1}/{len(bboxes)} - debut")
                
                pois = self._extract_from_bbox(
                    bbox, poi_types, tags_config, max_radius, max_tags_per_type
                )
                
                if pois:
                    new_count = 0
                    for poi in pois:
                        if poi.id not in seen:
                            seen.add(poi.id)
                            all_pois.append(poi)
                            new_count += 1
                    logger.info(f"Bbox {i+1}/{len(bboxes)}: {len(pois)} POI trouves ({new_count} nouveaux)")
                else:
                    logger.info(f"Bbox {i+1}/{len(bboxes)}: aucun POI")
                    
            except Exception as e:
                logger.error(f"Erreur bbox {i+1}: {e}")
            
            # Pause obligatoire entre chaque bbox
            if i < len(bboxes) - 1:
                pause = 3.0
                logger.debug(f"Pause de {pause}s avant la prochaine bbox")
                time.sleep(pause)
        
        logger.info(f"Total: {len(all_pois)} POI detectes")
        return all_pois
    
    def calculate_distances_to_track(self, pois: List[POI], track_points: List[Dict]) -> List[POI]:
        """Calcule les distances des POI par rapport a la trace"""
        if not pois or not track_points:
            return pois
        
        logger.info(f"Calcul distances: {len(pois)} POI")
        
        # Echantillonnage pour performance
        points = track_points[::10] if len(track_points) > 2000 else track_points
        
        for poi in pois:
            min_dist = float('inf')
            for point in points:
                dist = self._haversine_distance(
                    poi.lat, poi.lon,
                    point['latitude'], point['longitude']
                )
                if dist < min_dist:
                    min_dist = dist
                    if min_dist < 0.01:
                        break
            poi.distance = min_dist
        
        return pois
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance en km avec Haversine"""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
        return R * c
    
    def get_poi_statistics(self, pois: List[POI]) -> Dict[str, Any]:
        """Statistiques des POI"""
        stats = {
            'total': len(pois),
            'by_type': {},
            'by_osm_type': {},
            'named': 0,
            'unnamed': 0
        }
        
        distances = []
        for poi in pois:
            stats['by_type'][poi.type] = stats['by_type'].get(poi.type, 0) + 1
            stats['by_osm_type'][poi.osm_type] = stats['by_osm_type'].get(poi.osm_type, 0) + 1
            if poi.name:
                stats['named'] += 1
            else:
                stats['unnamed'] += 1
            if poi.distance is not None:
                distances.append(poi.distance)
        
        if distances:
            stats['distances'] = {
                'min': min(distances),
                'max': max(distances),
                'avg': sum(distances) / len(distances)
            }
        else:
            stats['distances'] = None
        
        return stats