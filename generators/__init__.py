#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .base_generator import BaseGenerator, GeneratorRegistry

def register_all_generators():
    from .report.json_generator import JSONGenerator
    from .report.csv_generator import CSVGenerator
    from .report.excel_generator import ExcelGenerator
    from .report.word_generator import WordGenerator
    from .report.word_map_generator import WordMapGenerator
    from .report.pdf_generator import PDFGenerator
    from .report.pdf_map_generator import PDFMapGenerator
    from .report.gdocs_generator import GDocsGenerator
    from .report.gdocs_map_generator import GDocsMapGenerator

    from .enriched.gpx_generator import GPXGenerator
    from .enriched.kml_generator import KMLGenerator
    from .enriched.tcx_generator import TCXGenerator
    from .enriched.fit_generator import FITGenerator

    GeneratorRegistry.register('json', JSONGenerator)
    GeneratorRegistry.register('csv', CSVGenerator)
    GeneratorRegistry.register('xlsx', ExcelGenerator)
    GeneratorRegistry.register('docx', WordGenerator)
    GeneratorRegistry.register('docx-map', WordMapGenerator)
    GeneratorRegistry.register('pdf', PDFGenerator)
    GeneratorRegistry.register('pdf-map', PDFMapGenerator)
    GeneratorRegistry.register('gdocs', GDocsGenerator)
    GeneratorRegistry.register('gdocs-map', GDocsMapGenerator)

    GeneratorRegistry.register('gpx-enriched', GPXGenerator)
    GeneratorRegistry.register('kml-enriched', KMLGenerator)
    GeneratorRegistry.register('tcx-enriched', TCXGenerator)
    GeneratorRegistry.register('fit-data', FITGenerator)

register_all_generators()