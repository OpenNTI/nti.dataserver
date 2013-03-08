# -*- coding: utf-8 -*-
"""
Content processing module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re

from zope import interface

from . import interfaces as cp_interfaces

# define global constants
default_ngram_minsize = 2
default_ngram_maxsize = 20 # average word size in English in 5.10 
default_word_tokenizer_expression = r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*"

default_punk_char_expression = r'[\?|!|(|)|"|\'|`|{|}|\[|\]|:|;|,|\.|\^|%|&|#|\*|@|$|&|+|\-|<|>|=|_|\~|\\|\s]'

default_word_tokenizer_pattern = re.compile(default_word_tokenizer_expression, re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

default_punk_char_pattern = re.compile(default_punk_char_expression, re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

# export common functions
from ._content_utils import rank_words
from ._ngrams_utils import compute_ngrams
from ._content_utils import split_content
from ._content_utils import get_content_translation_table

