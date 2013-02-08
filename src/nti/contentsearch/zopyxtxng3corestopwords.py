# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from zopyx.txng3.core.stopwords import Stopwords as zopyxStopWords

from nti.contentsearch import interfaces as search_interfaces

class _Stopwords(zopyxStopWords):
 
    def __init__(self):
        self._cache = {}
        ntisw = component.getUtility(search_interfaces.IStopWords)
        for language in ntisw.available_languages():
            words = ntisw.stopwords(language)
            words = {s.encode('utf-8').lower(): None for s in words}
            self._cache[language] = words

    def availableLanguages(self):
        ntisw = component.getUtility(search_interfaces.IStopWords)
        return ntisw.available_languages()
