# coding: utf-8
import warnings


def init():
    import numpy
    _ = numpy

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
