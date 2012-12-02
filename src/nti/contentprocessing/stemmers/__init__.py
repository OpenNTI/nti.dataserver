from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

import repoze.lru

from nti.contentprocessing.stemmers import interfaces as stemmer_interfaces

import logging
logger = logging.getLogger( __name__ )

@repoze.lru.lru_cache(1000)
def stem_word(word, name='porter'):
    stemmer = component.getUtility(stemmer_interfaces.IStemmer, name=name)
    result = stemmer.stem(unicode(word)) if word else None
    return result
