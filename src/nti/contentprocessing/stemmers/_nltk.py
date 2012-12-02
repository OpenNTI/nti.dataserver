from __future__ import print_function, unicode_literals

from zope import interface

import nltk

from nti.contentprocessing.stemmers import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class _PorterStemmer(object):
    def __init__(self):
        self.stemmer = nltk.PorterStemmer()
        
    def stem(self, token):
        token = unicode(token)
        result = self.stemmer.stem(token)
        return result if result else token

