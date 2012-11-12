from __future__ import print_function, unicode_literals

from zope import interface

from zopyx.txng3.ext import stemmer

from nti.contentprocessing.stemmers import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class ZopyYXStemmer(object):
    def __init__(self, language='english'):
        self._stemmer = stemmer.Stemmer(language)
        
    def stem(self, token):
        token = unicode(token)
        result = self._stemmer.stem((token,))
        return result[0] if result else token

if __name__ == '__main__':
    print(ZopyYXStemmer().stem('carlos'))