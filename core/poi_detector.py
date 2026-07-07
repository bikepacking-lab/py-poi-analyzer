#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor, as_completed

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
import random
from config import (
    AVAILABLE_POI_TAGS_OSM, 
    OVERPASS_DEBUG_MODE, 
    MAX_TAGS_PER_TYPE,
    OVERPASS_SERVERS,
    OVERPASS_SERVER_TIMEOUT
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
    """Rate limiting thread-safe avec jitter"""
    
    def __init__(self, max_requests_per_minute: int = 18):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval = 60.0 / max_requests_per_minute
        self.lock = threading.Lock()
        self.last_request_time = 0.0
    
    def wait(self):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            
            # Ajout de jitter pour eviter les requetes synchronisees
            jitter = random.uniform(0.8, 1.2)
            interval = self.min_interval * jitter
            
            if elapsed < interval:
                wait_time = interval - elapsed
                logger.debug(f"Rate limiting: attente {wait_time:.2f}s")
                time.sleep(wait_time)
            
            self.last_request_time = time.time()


class ServerManager:
    """Gestionnaire de serveurs Overpass avec fallback"""
    
    def __init__(self, servers: List[str]):
        self.servers = servers.copy()
        self.failed_servers = {}  # server_url -> timestamp
        self.lock = threading.Lock()
        self.index = 0
    
    def get_server(self) -> str:
        """Retourne un serveur disponible"""
        with self.lock:
            current_time = time.time()
            available_servers = []
            
            for server in self.servers:
                if server in self.failed_servers:
                    if current_time - self.failed_servers[server] > OVERPASS_SERVER_TIMEOUT:
                        del self.failed_servers[server]
                        available_servers.append(server)
                else:
                    available_servers.append(server)
            
            if not available_servers:
                logger.warning("Aucun serveur disponible, reinitialisation")
                self.failed_servers.clear()
                available_servers = self.servers.copy()
            
            server = available_servers[self.index % len(available_servers)]
            self.index += 1
            return server
    
    def mark_failed(self, server: str):
        """Marque un serveur comme ayant echoue"""
        with self.lock:
            self.failed_servers[server] = time.time()
            logger.warning(f"Serveur {server} marque comme defaillant")


class POIDetector:
    """Detecteur de Points d'Interet - Version optimisee"""
    
    def __init__(self, cache_manager=None):
        self.cache = cache_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PYPOIANALYSER/1.0 (contact: contact@bikepacking-analyzer.com)',
            'Accept': 'application/json'
        })
        
        # Rate limiting: 18 requetes par minute
        self.rate_limiter = RateLimiter(max_requests_per_minute=18)
        
        # Gestionnaire de serveurs
        self.server_manager = ServerManager(OVERPASS_SERVERS)
        
        # Configuration des retries
        self.max_retries = 5
        self.base_delay = 5.0
        self.max_delay = 120.0
        self.timeout = 90
        
        self.query_cache = {}
        self.cache_lock = threading.Lock()
        
        logger.info(f"POIDetector initialise (rate limit: 18 req/min, {len(OVERPASS_SERVERS)} serveurs)")
    
    def _get_server_url(self) -> str:
        """Retourne un serveur disponible"""
        return self.server_manager.get_server()
    
    def _mark_server_failed(self, server: str):
        """Marque un serveur comme ayant echoue"""
        self.server_manager.mark_failed(server)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calcule le backoff exponentiel avec jitter"""
        delay = self.base_delay * (2 ** attempt)  # 5, 10, 20, 40, 80
        delay = min(delay, self.max_delay)
        jitter = random.uniform(0.7, 1.3)
        return delay * jitter
    
    def _split_bbox(self, bbox: Tuple[float, float, float, float], max_size: float = 0.05) -> List[Tuple[float, float, float, float]]:
        """Decoupe une bbox volumineuse en sous-bboxes"""
        lat_min, lon_min, lat_max, lon_max = bbox
        
        lat_size = lat_max - lat_min
        lon_size = lon_max - lon_min
        
        if lat_size <= max_size and lon_size <= max_size:
            return [bbox]
        
        lat_div = max(1, math.ceil(lat_size / max_size))
        lon_div = max(1, math.ceil(lon_size / max_size))
        
        sub_bboxes = []
        lat_step = lat_size / lat_div
        lon_step = lon_size / lon_div
        
        for i in range(lat_div):
            for j in range(lon_div):
                sub_bbox = (
                    lat_min + i * lat_step,
                    lon_min + j * lon_step,
                    lat_min + (i + 1) * lat_step,
                    lon_min + (j + 1) * lon_step
                )
                sub_bboxes.append(sub_bbox)
        
        if OVERPASS_DEBUG_MODE:
            logger.debug(f"Bbox decoupee en {len(sub_bboxes)} sous-bboxes")
        return sub_bboxes
    
    def _build_overpass_query(self, bbox: Tuple[float, float, float, float], 
                             poi_types: List[str], 
                             tags_config: Dict,
                             max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> str:
        """Construit une requete Overpass"""
        lat_min, lon_min, lat_max, lon_max = bbox
        bbox_str = f"{lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}"
        
        queries = []

        if OVERPASS_DEBUG_MODE:
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
            
            if OVERPASS_DEBUG_MODE:
                logger.info(f"Type '{poi_type}' - {len(tags_list)} tags disponibles")
                logger.info(f"  Tags utilises ({len(tags_list)}):")
                for i, tag in enumerate(tags_list):
                    logger.info(f"    {i+1}. {tag}")
            
            for tag_filter in tags_list:
                tag_clean = tag_filter.strip()
                queries.append(f'node{tag_clean}({bbox_str});')
                queries.append(f'way{tag_clean}({bbox_str});')
                queries.append(f'relation{tag_clean}({bbox_str});')
                
        if not queries:
            return ''
        
        query = '[out:json][timeout:25];\n(\n'
        query += '\n'.join(queries)
        query += '\n);\nout body qt;'
        
        if OVERPASS_DEBUG_MODE:
            logger.info(f"Requete construite ({len(queries)} sous-requetes)")
            logger.debug(f"Requete complete: {query[:500]}...")

        return query
    
    def _query_overpass(self, query: str) -> Optional[List[Dict]]:
        """Execute une requete Overpass avec retry, backoff, jitter et round-robin"""
        
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
                # Rate limiting avant chaque requete
                self.rate_limiter.wait()
                
                # Selection du serveur en round-robin
                server_url = self._get_server_url()
                
                response = self.session.post(
                    server_url,
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
                            delay = self._calculate_backoff(attempt)
                            time.sleep(delay)
                        continue
                
                elif response.status_code == 504:
                    delay = self._calculate_backoff(attempt) + 10
                    logger.warning(f"Gateway Timeout 504 (serveur {server_url}), attente {delay:.1f}s ({attempt+1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                    
                elif response.status_code == 429:
                    # Attente reelle de 25s + backoff
                    delay = 25.0 + self._calculate_backoff(attempt)
                    logger.warning(f"Rate limit 429 (serveur {server_url}), attente {delay:.1f}s ({attempt+1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                    
                elif response.status_code == 400:
                    logger.error(f"Bad Request (serveur {server_url}): {response.text[:200]}")
                    return None
                    
                elif response.status_code in [500, 502, 503]:
                    # Marquer le serveur comme defaillant
                    self._mark_server_failed(server_url)
                    delay = self._calculate_backoff(attempt) + 5
                    logger.warning(f"Erreur serveur {response.status_code}, attente {delay:.1f}s")
                    time.sleep(delay)
                    continue
                    
                else:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        time.sleep(delay)
                    continue
                
            except requests.Timeout:
                delay = self._calculate_backoff(attempt) + 5
                logger.warning(f"Timeout ({attempt+1}/{self.max_retries}), attente {delay:.1f}s")
                time.sleep(delay)
                continue
            except requests.RequestException as e:
                # Marquer le serveur comme defaillant
                self._mark_server_failed(server_url if 'server_url' in locals() else 'unknown')
                delay = self._calculate_backoff(attempt)
                logger.warning(f"Erreur requete: {e}, attente {delay:.1f}s")
                time.sleep(delay)
                continue
            except Exception as e:
                logger.error(f"Erreur inattendue: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
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
                
                if not self._match_type(tags, poi_type):
                    continue
            
                lat = element.get('lat', 0.0)
                lon = element.get('lon', 0.0)
            
                if lat == 0.0 and lon == 0.0:
                    continue
                if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                    continue
            
                name = tags.get('name') or tags.get('ref')
                if not name and not tags:
                    continue
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
        
            if not conditions:
                return False
        
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
        
            if total == 1:
                return matched >= 1
            else:
                return matched >= total / 2
        except Exception:
            return False
    
    def _extract_from_bbox(self, bbox: Tuple[float, float, float, float], 
                          poi_types: List[str], 
                          tags_config: Dict,
                          radius: float,
                          max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> List[POI]:
        """Extrait les POI d'une bbox avec decoupage si necessaire"""
        if not bbox or not poi_types:
            return []
        
        # Cache Redis
        cache_key = f"poi:{bbox}:{','.join(sorted(poi_types))}:{max_tags_per_type}"
        cached = self.cache.get(cache_key) if self.cache else None
        if cached:
            logger.debug(f"Cache Redis hit")
            return [POI(**p) for p in cached]
        
        # Decoupage de la bbox si trop grande
        sub_bboxes = self._split_bbox(bbox)
        
        all_pois = []
        for sub_bbox in sub_bboxes:
            query = self._build_overpass_query(sub_bbox, poi_types, tags_config, max_tags_per_type)
            if not query:
                continue
            
            elements = self._query_overpass(query)
            if not elements:
                continue
            
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
                   max_workers: int = 2,
                   max_tags_per_type: int = MAX_TAGS_PER_TYPE) -> List[POI]:
        """
        Detecte les POI avec gestion robuste des erreurs
        """
        if not bboxes or not poi_types:
            return []
        
        effective_workers = min(max_workers, 2)
        logger.info(f"Detection POI: {len(bboxes)} bboxes, workers={effective_workers}")
        
        all_pois = []
        seen = set()
        max_radius = max(radii.values()) if radii else 0.0
        
        # Melange des bboxes pour repartir la charge
        random.shuffle(bboxes)
        
        # Decoupage des bboxes volumineuses
        all_sub_bboxes = []
        for bbox in bboxes:
            sub_bboxes = self._split_bbox(bbox)
            all_sub_bboxes.extend(sub_bboxes)
        
        if OVERPASS_DEBUG_MODE:
            logger.info(f"Total sous-bboxes: {len(all_sub_bboxes)}")
        
        if effective_workers == 1:
            # Mode serie
            for i, sub_bbox in enumerate(all_sub_bboxes):
                try:
                    logger.info(f"Sous-bbox {i+1}/{len(all_sub_bboxes)} - debut")
                    
                    pois = self._extract_from_bbox(
                        sub_bbox, poi_types, tags_config, max_radius, max_tags_per_type
                    )
                    
                    if pois:
                        new_count = 0
                        for poi in pois:
                            if poi.id not in seen:
                                seen.add(poi.id)
                                all_pois.append(poi)
                                new_count += 1
                        logger.info(f"Sous-bbox {i+1}: {len(pois)} POI trouves ({new_count} nouveaux)")
                    else:
                        logger.info(f"Sous-bbox {i+1}: aucun POI")
                    
                except Exception as e:
                    logger.error(f"Erreur sous-bbox {i+1}: {e}")
            
                if i < len(all_sub_bboxes) - 1:
                    pause = random.uniform(2.0, 5.0)
                    logger.debug(f"Pause de {pause:.1f}s avant la prochaine sous-bbox")
                    time.sleep(pause)
        else:
            # Mode parallele
            with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                futures = []
                for i, sub_bbox in enumerate(all_sub_bboxes):
                    if i > 0:
                        delay = random.uniform(1.0, 3.0)
                        time.sleep(delay)
                    
                    future = executor.submit(
                        self._extract_from_bbox,
                        sub_bbox, poi_types, tags_config, max_radius, max_tags_per_type
                    )
                    futures.append(future)
            
                for future in as_completed(futures):
                    try:
                        pois = future.result(timeout=90)
                        for poi in pois:
                            if poi.id not in seen:
                                seen.add(poi.id)
                                all_pois.append(poi)
                    except Exception as e:
                        logger.error(f"Erreur parallele: {e}")
        
        logger.info(f"Total: {len(all_pois)} POI detectes")
        return all_pois
    
    def calculate_distances_to_track(self, pois: List[POI], track_points: List[Dict]) -> List[POI]:
        """Calcule les distances des POI par rapport a la trace"""
        if not pois or not track_points:
            return pois
        
        logger.info(f"Calcul distances: {len(pois)} POI")
        
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