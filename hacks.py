# coding: utf-8
import sys
import warnings

in_bundle = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def init():
    import numpy
    _ = numpy

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
