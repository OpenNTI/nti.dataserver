from __future__ import print_function, unicode_literals

from zope import interface

from nti.contentsearch.spambayes import interfaces as sps_interfaces

@interface.implementer(sps_interfaces.ITokenizerSettings)
class _DefaultTokenizerSettings(object):
	min_word_size = 3
	max_word_size = 12
	short_runs = False
	generate_long_skips = True
	replace_nonascii_chars = True
	
@interface.implementer(sps_interfaces.IClassifierSettings)
class _DefaultClassifierSettings(_DefaultTokenizerSettings):
	use_bigrams = False
	arc_discriminators = 50
	max_discriminators = 150
	unknown_word_strength = 0.45	
	unknown_word_probability = 0.5
	minimum_probability_strength = 0.10