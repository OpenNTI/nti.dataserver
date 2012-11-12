from __future__ import print_function, unicode_literals

from zope import interface

from nltk import PorterStemmer

from nti.contentrendering.stemmers._zopyx import ZopyYXStemmer
from nti.contentrendering.stemmers import interfaces as stemmer_interfaces

interface.alsoProvides(PorterStemmer, stemmer_interfaces.IStemmer )
