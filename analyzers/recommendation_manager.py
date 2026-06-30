#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class RecommendationManager:
    """Gestionnaire des recommandations"""
    
    @staticmethod
    def generate(poi_stats: Dict[str, Any], poi_types: List[str], radii: Dict[str, float]) -> List[str]:
        """
        Genere des recommandations pour affiner la recherche
        """
        recommendations = []
        
        if not poi_stats:
            return recommendations
        
        total = poi_stats.get('total', 0)
        
        if total == 0:
            recommendations.append("Aucun POI trouve. Augmentez les rayons de recherche ou elargissez les bbox.")
            recommendations.append("Verifiez les tags OSM configures pour les types: " + ", ".join(poi_types))
            return recommendations
        
        # Recommandations par type
        by_type = poi_stats.get('by_type', {})
        for poi_type in poi_types:
            count = by_type.get(poi_type, 0)
            radius = radii.get(poi_type, 0.0)
            
            if count == 0:
                recommendations.append(
                    f"Aucun POI de type '{poi_type}' trouve (rayon: {radius:.0f}m). "
                    f"Augmentez le rayon ou verifiez les tags OSM."
                )
            elif count < 5:
                recommendations.append(
                    f"Peu de POI de type '{poi_type}' ({count}). "
                    f"Rayon actuel: {radius:.0f}m. Envisagez d'augmenter a {int(radius * 1.5)}m."
                )
            else:
                recommendations.append(
                    f"POI de type '{poi_type}' satisfaisant: {count} trouves."
                )
        
        # Recommandations sur les distances
        distances = poi_stats.get('distances')
        if distances and isinstance(distances, dict):
            avg_dist = distances.get('avg')
            if avg_dist is not None:
                try:
                    avg_dist = float(avg_dist)
                    if avg_dist > 2.0:
                        recommendations.append(
                            f"Distance moyenne des POI: {avg_dist:.2f} km. "
                            f"Les POI sont eloignes de la trace. Envisagez de reduire l'intervalle de recherche."
                        )
                    elif avg_dist < 0.1:
                        recommendations.append(
                            f"Distance moyenne des POI: {avg_dist:.2f} km. "
                            f"Les POI sont tres proches de la trace. La recherche est bien parametree."
                        )
                except (ValueError, TypeError):
                    pass
        
        return recommendations