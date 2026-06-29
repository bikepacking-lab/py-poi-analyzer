#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS Trace Analyzer
Analyseur de traces GPS avec détection de Points d'Intérêt
"""

__version__ = '1.0.0'
__author__ = 'GPS Analyzer Team'

from analyzers.track_analyzer import TrackAnalyzer
from core.poi_detector import POI
from config import BASE_DIR, GPX_DIR, REPORT_DIR

__all__ = [
    'TrackAnalyzer',
    'POI',
    'BASE_DIR',
    'GPX_DIR',
    'REPORT_DIR'
]