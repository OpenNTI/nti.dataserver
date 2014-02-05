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


# define global constants
default_ngram_minsize = 2
default_ngram_maxsize = 20  # average word size in English in 5.10
default_word_tokenizer_expression = r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*"

default_punk_char_expression = (ur'[\?|!|(|)|"|\''
								u'|\u2039|\u203a' # single angle quotes
								u'|\u2018|\u2019' # single curly quotes
								u'|\u201c|\u201d' # double curly quotes
								u'|\u00ab|\u00bb' # double angle quotes
								ur'|`|{|}|\[|\]|:|;|,|\.|\^|%|&|#|\*|@|'
								u'$|\u20ac' # dollar and euro
								ur'|&|+|\-|<|>|=|_|\~|\\|/|\|]')

default_punk_char_expression_plus = (default_punk_char_expression[:-1] +
									 ur'|\s'
									 ur'|\u200b|\u2060]') # zero-width space, word joiner

default_word_tokenizer_pattern = re.compile(default_word_tokenizer_expression,
											re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

default_punk_char_pattern = re.compile(default_punk_char_expression,
									   re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

default_punk_char_pattern_plus = re.compile(default_punk_char_expression_plus,
											re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

space_pattern = re.compile(r'\s+', re.UNICODE)

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
