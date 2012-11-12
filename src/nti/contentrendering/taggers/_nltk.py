from __future__ import print_function, unicode_literals

import os
import gzip 
import pickle
import inspect

from zope import component
from zope import interface

import repoze.lru

from nltk.tag import DefaultTagger, NgramTagger

from nti.contentrendering.taggers import interfaces as tagger_interfaces

import logging
logger = logging.getLogger( __name__ )

def nltk_tagged_corpora():
    result = {}
    try:
        from nltk import corpus
        from nltk.corpus import LazyCorpusLoader, CorpusReader
        for k, v in inspect.getmembers(corpus):
            if  isinstance(v, (LazyCorpusLoader, CorpusReader)) and \
                hasattr(v,"tagged_sents") and hasattr(v,"tagged_words"):
                result[k] = v
                interface.alsoProvides( v, tagger_interfaces.ITaggedCorpus )
    except:
        logger.error("Error importing nltk corpora")
    return result
    
def get_nltk_tagged_corpus(corpus="brown"):
    return nltk_tagged_corpora().get(corpus)
     
@interface.implementer(tagger_interfaces.INLTKTaggedSents)
class _NLTKTaggedSents(object):
    
    def __init__(self):
        self.tagged_sents = {}
    
    def __call__(self, corpus="brown", limit=-1):
        sents = self.tagged_sents.get(corpus, None)
        if sents is None:
            corpus = get_nltk_tagged_corpus(corpus)
            sents = corpus.tagged_sents() if corpus is not None else ()
            self.tagged_sents[corpus] = []
        return sents[:limit] if limit >= 0 else sents
    
def get_training_sents(corpus="brown", limit=-1):
    util = component.queryUtility(tagger_interfaces.INLTKTaggedSents)
    util = util or _NLTKTaggedSents()
    return util(corpus, limit)

def load_tagger_pickle(name):
    result = None
    if os.path.exists(name):
        with gzip.open(name,"rb") as f:
            result = pickle.load(f)
    return result

@repoze.lru.lru_cache(50)
@interface.implementer(tagger_interfaces.INLTKBackoffNgramTagger)
def get_backoff_ngram_tagger(ngrams=3, corpus="brown", limit=-1, train_sents=None):
    
    tagger = None
    if not train_sents:
        # check for a trained tagger
        name = "ngrams.%s.%s.%s.pickle.gz" %  (ngrams, corpus, limit)
        name = os.path.join(os.path.dirname(__file__),  name)
        tagger = load_tagger_pickle(name)
    
    if tagger is None:
        if not train_sents:
            train_sents = get_training_sents(corpus, limit)
            
        tagger = DefaultTagger('NN')
        for n in range(1, ngrams+1):
            tagger = NgramTagger(n, train=train_sents, backoff=tagger)
            
    return tagger

if __name__ == '__main__':
    pass
