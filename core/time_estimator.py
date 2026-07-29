#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional
import math

from config import (
    DEFAULT_SPEEDS, 
    DEFAULT_BREAKS_PER_HOUR, 
    DEFAULT_ACTIVITY_TYPE, 
    DEFAULT_DAY_DURATION_HOURS
)

class TimeEstimator:
    """Estimateur de temps de parcours"""
    
    @staticmethod
    def estimate_time(
        distance_km: float,
        total_ascent_m: float = 0,
        speed_kmh: Optional[float] = None,
        activity_type: Optional[str] = None,
        breaks_per_hour: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Estime le temps de parcours
        
        Args:
            distance_km: Distance en kilomètres
            total_ascent_m: Dénivelé positif en mètres
            speed_kmh: Vitesse en km/h (si None, utilise la valeur par défaut)
            activity_type: Type d'activité (cycling, mtb, hiking, etc.)
            breaks_per_hour: Minutes de pause par heure
            
        Returns:
            Dictionnaire avec les temps estimés
        """
        if distance_km <= 0:
            return {
                'moving_hours': 0,
                'moving_minutes': 0,
                'total_hours': 0,
                'total_minutes': 0,
                'break_minutes': 0,
                'average_speed_kmh': 0,
                'pace_min_per_km': 0,
                'formatted_moving': '0h 0min',
                'formatted_total': '0h 0min',
                'formatted_moving_dhm': '0h 0min',
                'formatted_total_dhm': '0h 0min'
            }
        
        # Vitesse
        if speed_kmh is None or speed_kmh <= 0:
            speeds = DEFAULT_SPEEDS
            if activity_type and activity_type in speeds:
                speed_kmh = speeds[activity_type]
            else:
                speed_kmh = speeds.get('default', 15.0)
        
        # Ajustement de la vitesse en fonction du dénivelé
        # +1000m de dénivelé réduit la vitesse d'environ 15%
        if total_ascent_m > 0:
            ascent_factor = 1.0 - (min(total_ascent_m, 3000) / 3000) * 0.25
            adjusted_speed = speed_kmh * max(ascent_factor, 0.6)
        else:
            adjusted_speed = speed_kmh
        
        # Temps de déplacement
        moving_hours = distance_km / adjusted_speed
        moving_minutes = moving_hours * 60
        moving_seconds = moving_minutes * 60
        
        
        # Pauses
        break_minutes = (moving_hours * (breaks_per_hour or DEFAULT_BREAKS_PER_HOUR))
        total_minutes = moving_minutes + break_minutes
        total_hours = total_minutes / 60
        total_seconds = total_minutes * 60
        
        
        # Allure (min/km)
        pace = moving_minutes / distance_km if distance_km > 0 else 0
        
        return {
            'moving_hours': round(moving_hours, 2),
            'moving_minutes': round(moving_minutes, 1),
            'total_hours': round(total_hours, 2),
            'total_minutes': round(total_minutes, 1),
            'break_minutes': round(break_minutes, 1),
            'average_speed_kmh': round(adjusted_speed, 1),
            'pace_min_per_km': round(pace, 1),
            'formatted_moving': round(moving_seconds,1),
            'formatted_total': round(total_seconds,1),
            'activity_type': activity_type or DEFAULT_ACTIVITY_TYPE,
            'formatted_moving_dhm': TimeEstimator._format_time(moving_minutes),
            'formatted_total_dhm': TimeEstimator._format_time(total_minutes)
        }
    
    @staticmethod
    def _format_time(minutes: float) -> str:
        """Formate un temps en heures et minutes"""
        if minutes < 1:
            return '0 min'
        
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0 and mins > 0:
            return f"{hours}h {mins}min"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{mins}min"
    
    @staticmethod
    def estimate_total_time_(seconds, activity="gravel"):
        """
        Estime le temps total en jours, heures et minutes
        """
        if activity not in DEFAULT_DAY_DURATION_HOURS:
            activity = "default"
        
        h_day = DEFAULT_DAY_DURATION_HOURS.get(activity, 8.0)

        hours = seconds / 3600

        days = int(hours // h_day)
        modulo = hours % h_day

        h = int(modulo)
        m = int((modulo - h) * 60)

        return days, h, m