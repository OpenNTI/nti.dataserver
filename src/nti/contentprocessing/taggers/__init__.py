# -*- coding: utf-8 -*-
"""
POS tagger module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import repoze.lru

from zope import component

from . import interfaces as tagger_interfaces

@repoze.lru.lru_cache(1000)
def tag_word(word, language=u'en'):
    return tag_tokens([word], language)

def tag_tokens(tokens, language=u'en'):
    tagger = component.getUtility(tagger_interfaces.ITagger, name=language)
    result = tagger.tag(tokens) if tokens else ()
    return result
