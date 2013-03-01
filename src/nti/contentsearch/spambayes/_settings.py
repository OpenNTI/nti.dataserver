# -*- coding: utf-8 -*-
"""
Spambayes object settings

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from . import interfaces as sps_interfaces

@interface.implementer(sps_interfaces.ITokenizerSettings)
class _DefaultTokenizerSettings(object):
	min_word_size = 3
	max_word_size = 12
	short_runs = False
	generate_long_skips = True
	replace_nonascii_chars = True
	
@interface.implementer(sps_interfaces.IClassifierSettings)
class _DefaultClassifierSettings(object):
	use_bigrams = False
	arc_discriminators = 50
	max_discriminators = 150
	unknown_word_strength = 0.45	
	unknown_word_probability = 0.5
	minimum_probability_strength = 0.10
	
@interface.implementer(sps_interfaces.IHistogramSettings)
class _DefaultHistogramSettings(object):
	buckets = 200
	percentiles = (5, 25, 75, 95)
