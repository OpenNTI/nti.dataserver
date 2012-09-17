#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
logger = __import__( 'logging' ).getLogger( __name__ )

from zope import component
from . import interfaces
from . import term

def lookup( info, dictionary=None ):
	"""
	Given a WordInfo, fills it in.

	:param info: A :class:`nti.dictserver.term.DictionaryTerm` or a string.
	:param dictionary: Implementation of :class:`interfaces.IDictionaryTermDataStorage` or None.
		If None, we look for a storage as the default utility.

	:return: A :class:`nti.dictserver.term.DictionaryTerm` with the definition filled in.
		We will not overwrite existing fields like ``ipa`` with blank entries if you pass in
		an existing DictionaryTerm, but we will add supplemental infos.
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

	info.ipa = data.get('ipa') if not info.ipa else info.ipa
	info.etymology = data.get('etymology') if not info.etymology else info.etymology

	dictInfo = term.DictInfo()

	for meaning in data.get('meanings',()):
		meaning.setdefault( 'examples', [] )
		dictInfo.addDefinition( term.DefInfo( [(meaning['content'], meaning.get('examples',()))],
											  meaning['type'] ) )
	if dictInfo:
		info.addInfo( dictInfo )

	if info.findInfo( term.LinkInfo ) is None:
		info.addInfo( term.LinkInfo( 'http://www.google.com/search?q=' + info.word ) )

	therInfo = term.TherInfo()
	for synonym in data.get('synonyms',()):
		therInfo.addSynonym( synonym )

	if therInfo:
		info.addInfo( therInfo )

	return info
