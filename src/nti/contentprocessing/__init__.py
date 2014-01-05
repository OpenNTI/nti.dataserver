# -*- coding: utf-8 -*-
"""
Content processing module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import sys
import unicodedata

from zope import interface

from . import interfaces as cp_interfaces

# define global constants
default_ngram_minsize = 2
default_ngram_maxsize = 20  # average word size in English in 5.10
default_word_tokenizer_expression = r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*"

default_punk_char_expression = \
	r'[\?|!|(|)|"|\'|`|{|}|\[|\]|:|;|,|\.|\^|%|&|#|\*|@|$|&|+|\-|<|>|=|_|\~|\\|/|\|]'

default_punk_char_expression_plus =\
	r'[\?|!|(|)|"|\'|`|{|}|\[|\]|:|;|,|\.|\^|%|&|#|\*|@|$|&|+|\-|<|>|=|_|\~|\\|/|\||\s]'

default_word_tokenizer_pattern = re.compile(default_word_tokenizer_expression, 
											re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

default_punk_char_pattern = re.compile(default_punk_char_expression,
									   re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

default_punk_char_pattern_plus = re.compile(default_punk_char_expression_plus, 
											re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

space_pattern = re.compile('\s+', re.UNICODE)

def _makenon_alpha_re():
	non_alpha = [u'[^']
	for i in range(sys.maxunicode):
		c = unichr(i)
		if c.isalpha(): non_alpha.append(c)
		non_alpha.append(u']')
	non_alpha = u"".join(non_alpha)
	return re.compile(non_alpha, re.UNICODE)

non_alpha_pattern = _makenon_alpha_re()
del _makenon_alpha_re

# export common functions
from .content_utils import normalize
from .content_utils import rank_words
from .content_utils import split_content
from .ngrams_utils import compute_ngrams
from .content_utils import get_content_translation_table
