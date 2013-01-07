from __future__ import print_function, unicode_literals

from zope import interface

from nti.contentprocessing.concepttagging import interfaces as cpct_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer( cpct_interfaces.IConceptSource )
class ConceptSource(object):
	
	def __init__(self, source, uri=None,):
		self.uri= uri
		self.source = source

	def __repr__( self ):
		return '%s(%s, %s)' % (self.__class__, self.source, self.uri)


@interface.implementer( cpct_interfaces.IConcept )
class Concept(object):
	
	def __init__(self, text, relevance, sources=()):
		self.text= text
		self.sources = sources
		self.relevance = relevance
	
	@property
	def sourcemap(self):
		result = {c.source:c.uri for c in self.sources}
		return result
	
	def __str__( self ):
		return self.text

	def __repr__( self ):
		return '%s(text=%s, relevance=%s, sources=%r)' % (self.__class__, self.text, self.relevance, self.sources)
