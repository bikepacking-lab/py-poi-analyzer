#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class BaseGenerator(ABC):
    """Classe de base pour tous les générateurs"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_format_type(self) -> str:
        """Retourne le type de format"""
        pass
    
    @abstractmethod
    def generate(self, data: Dict[str, Any], output_dir: Path, **kwargs) -> Optional[Path]:
        """Génère le fichier de sortie"""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Valide les données avant génération"""
        return True
    
    def pre_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prétraitement des données"""
        return data

class GeneratorRegistry:
    """Registre des générateurs"""
    
    _generators = {}
    
    @classmethod
    def register(cls, format_type: str, generator_class):
        cls._generators[format_type] = generator_class
        logger.debug(f"Générateur enregistré: {format_type}")
    
    @classmethod
    def get_generator(cls, format_type: str) -> Optional[BaseGenerator]:
        generator_class = cls._generators.get(format_type)
        if generator_class:
            return generator_class()
        return None
    
    @classmethod
    def get_all_generators(cls) -> List[str]:
        return list(cls._generators.keys())