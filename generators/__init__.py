#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .base_generator import GeneratorRegistry

def register_all_generators():
    # Rapports
    from .reporters.json_generator import JSONGenerator
    from .reporters.csv_generator import CSVGenerator
    from .reporters.excel_generator import ExcelGenerator
    from .reporters.word_generator import WordGenerator
    from .reporters.word_map_generator import WordMapGenerator
    from .reporters.gdocs_generator import GDocsGenerator
    from .reporters.gdocs_map_generator import GDocsMapGenerator
    from .reporters.pdf_generator import PDFGenerator
    from .reporters.pdf_map_generator import PDFMapGenerator
    
    # Enrichis
    from .enriched.gpx_generator import GPXGenerator as GPXEnrichedGenerator
    from .enriched.kml_generator import KMLGenerator as KMLEnrichedGenerator
    from .enriched.tcx_generator import TCXGenerator as TCXEnrichedGenerator
    from .enriched.fit_generator import FITGenerator as FITEnrichedGenerator
    
    # Conversions
    from .converters.gpx_converter import GPXConverter
    from .converters.kml_converter import KMLConverter
    from .converters.tcx_converter import TCXConverter
    from .converters.fit_converter import FITConverter

    # Rapports
    GeneratorRegistry.register('json', JSONGenerator)
    GeneratorRegistry.register('csv', CSVGenerator)
    GeneratorRegistry.register('xlsx', ExcelGenerator)
    GeneratorRegistry.register('docx', WordGenerator)
    GeneratorRegistry.register('docx-map', WordMapGenerator)
    GeneratorRegistry.register('gdocs', GDocsGenerator)
    GeneratorRegistry.register('gdocs-map', GDocsMapGenerator)
    GeneratorRegistry.register('pdf', PDFGenerator)
    GeneratorRegistry.register('pdf-map', PDFMapGenerator)
    
    # Enrichis
    GeneratorRegistry.register('gpx-enriched', GPXEnrichedGenerator)
    GeneratorRegistry.register('kml-enriched', KMLEnrichedGenerator)
    GeneratorRegistry.register('tcx-enriched', TCXEnrichedGenerator)
    GeneratorRegistry.register('fit-enriched', FITEnrichedGenerator)
    
    # Conversions
    GeneratorRegistry.register('gpx', GPXConverter)
    GeneratorRegistry.register('kml', KMLConverter)
    GeneratorRegistry.register('tcx', TCXConverter)
    GeneratorRegistry.register('fit', FITConverter)

register_all_generators()