#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class PlaceResolver:
    """Résout les coordonnées en lieux via le service Nominatim d'OpenStreetMap."""

    _request_lock = threading.Lock()
    _last_request_time = 0.0
    _minimum_request_interval_seconds = 1.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PYPOIANALYSER/1.0 (contact: contact@bikepacking-analyzer.com)',
            'Accept': 'application/json'
        })
        self._cache: Dict[Tuple[float, float], Optional[Dict[str, Any]]] = {}

    def resolve(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Retourne le nom et l'adresse lisible d'un lieu, ou None si indisponible."""
        cache_key = (round(latitude, 5), round(longitude, 5))
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with self._request_lock:
                wait_seconds = self._minimum_request_interval_seconds - (
                    time.monotonic() - self._last_request_time
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                type(self)._last_request_time = time.monotonic()
                response = self.session.get(
                    'https://nominatim.openstreetmap.org/reverse',
                    params={
                        'format': 'jsonv2',
                        'lat': latitude,
                        'lon': longitude,
                        'zoom': 10,
                        'addressdetails': 1
                    },
                    timeout=10
                )
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as error:
            logger.warning(
                "Géocodage inverse impossible pour %.5f, %.5f: %s",
                latitude, longitude, error
            )
            self._cache[cache_key] = None
            return None

        if not isinstance(result, dict) or not result.get('address'):
            logger.warning(
                "Aucun lieu trouvé par Nominatim pour %.5f, %.5f",
                latitude, longitude
            )
            self._cache[cache_key] = None
            return None

        address = result['address']
        if not isinstance(address, dict):
            logger.warning(
                "Adresse Nominatim invalide pour %.5f, %.5f",
                latitude, longitude
            )
            self._cache[cache_key] = None
            return None

        name = next(
            (
                address[key]
                for key in (
                    'hamlet', 'isolated_dwelling', 'village', 'town',
                    'city', 'municipality', 'locality', 'suburb'
                )
                if address.get(key)
            ),
            result.get('name')
        )
        place = {
            'latitude': latitude,
            'longitude': longitude,
            'name': name,
            'display_name': result.get('display_name'),
            'address': address
        }
        self._cache[cache_key] = place
        return place
