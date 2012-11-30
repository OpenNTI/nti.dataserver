from __future__ import print_function, unicode_literals, absolute_import

import re

import logging
logger = logging.getLogger( __name__ )

# define global constants
default_ngram_minsize = 2
default_ngram_maxsize = 20 # average word size in English in 5.10 
default_word_tokenizer_expression = r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*"

default_punk_char_expression = r'[\?|!|(|)|"|\'|`|{|}|\[|\]|:|;|,|\.|\^|%|&|#|\*|@|$|&|+|\-|<|>|=|_|\~|\\|\s]'

default_word_tokenizer_pattern = re.compile(default_word_tokenizer_expression, re.I | re.MULTILINE | re.DOTALL | re.UNICODE)

# export common functions
from nti.contentprocessing._content_utils import rank_words
from nti.contentprocessing._ngrams_utils import compute_ngrams
from nti.contentprocessing._content_utils import split_content
from nti.contentprocessing._content_utils import get_content_translation_table
