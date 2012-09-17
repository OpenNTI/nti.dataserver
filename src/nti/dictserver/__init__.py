#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

logger = __import__( 'logging' ).getLogger( __name__ )

from zope import component
from . import interfaces
from . import term

def lookup( info, dictionary=None ):
	"""
	Given a WordInfo, fills it in.

	:param info: A :class:`WordInfo` or a string.
	:param dictionary: Implementation of :class:`interfaces.IDictionaryTermDataStorage` or None.
	:return: A :class:`WordInfo` with the definition filled in.
	"""
	if isinstance( info, basestring ):
		info = term.DictionaryTerm( info )

	if dictionary is None:
		dictionary = component.queryUtility( interfaces.IDictionaryTermDataStorage )

	if dictionary is None: # pragma: no cover
		logger.debug( "No dictionary, returning empty results" )

	data = dictionary.lookup( info.word ) if dictionary is not None else None
	if data is None:
		data = {}

	info.ipa = data.get('ipa')
	info.etymology = data.get('etymology')
	dictInfo = term.DictInfo()
	for meaning in data.get('meanings',()):
		meaning.setdefault( 'examples', [] )
		dictInfo.addDefinition( term.DefInfo( [(meaning['content'], meaning.get('examples',()))],
											  meaning['type'] ) )
	info.addInfo( dictInfo )
	info.addInfo( term.LinkInfo( 'http://www.google.com/search?q=' + info.word ) )
	therInfo = term.TherInfo()
	info.addInfo( therInfo )
	for synonym in data.get('synonyms',()):
		therInfo.addSynonym( synonym )

	return info
