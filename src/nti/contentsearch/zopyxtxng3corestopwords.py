###########################################################################
# TextIndexNG V 3                
# The next generation TextIndex for Zope
#
# This software is governed by a license. See
# LICENSE.txt for the terms of this license.
###########################################################################

from zope import component

from zopyx.txng3.core.stopwords import Stopwords as zopyxStopWords

from nti.contentsearch import interfaces as search_interfaces

class _Stopwords(zopyxStopWords):
 
    def __init__(self):
        self._cache = {}
        ntisw = component.getUtility(search_interfaces.IStopWords)
        for language in ntisw.available_languages():
            words = ntisw.stopwords(language)
            words = {s.encode('iso-8859-15'): None for s in words}
            self._cache[language] = words

    def availableLanguages(self):
        ntisw = component.getUtility(search_interfaces.IStopWords)
        return ntisw.available_languages()
