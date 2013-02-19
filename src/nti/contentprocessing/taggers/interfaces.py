# -*- coding: utf-8 -*-
"""
POS tagger interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

class ITagger(interface.Interface):
    """
    Defines a POS tagger
    """
    def tag(tokens):
        """tag the specified tokens"""
        
class INLTKTaggedSents(interface.Interface):
    
    def __call__(corpus):
        """return tagged sents for the specified corpus"""
       
class ITaggedCorpus(interface.Interface):
    """Define a POS tagged corpus."""
    
    def tagged_words():
        """return a list of POS tagged words"""
        
    def tagged_sents():
        """return a list of POS tagged sentences"""
           
class INLTKBackoffNgramTagger(ITagger):
    pass
        
class INLTKBackoffNgramTaggerFactory(interface.Interface):
    
    def __call__(ngrams, corpus, train_sents, limit):
        """
        Create and train a backoff ngram tagger
        
        :param ngrams Number of ngrams
        :param corpus Optional corpus name
        :param train_sents: Training tagged sents
        :param limit Max munber of training sents
        """