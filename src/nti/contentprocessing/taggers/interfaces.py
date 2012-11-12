from __future__ import unicode_literals, print_function

from zope import interface

class INLTKTaggedSents(interface.Interface):
    def __call__(corpus):
        """return tagged sents for the specified corpus"""
       
class ITaggedCorpus(interface.Interface):
    """Define a POS tagged corpus."""
    
    def tagged_words():
        """return a list of POS tagged words"""
        
    def tagged_sents():
        """return a list of POS tagged sentences"""
         
class INLTKBackoffNgramTagger(interface.Interface):
    def __call__(ngrams, corpus, train_sents, limit):
        """
        Create and train a backoff ngram tagger
        
        :param ngrams Number of ngrams
        :param corpus Optiona corpus name
        :param train_sents: Training tagged sents
        :param limit Max munber of training sents
        """