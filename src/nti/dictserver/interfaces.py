#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces for the dictionary/glossary component.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


from zope import interface
from zope.interface.common.mapping import IReadMapping
from zope import schema

class IDictionaryTermData(IReadMapping):
	"""
	A 'raw' term stored in a dictionary. Has some or all
	of these keys:

	meanings
		A sequence of meaning dictionaries, each with the keys
		``content``, ``examples`` and ``type`` (where type is actually
		the part of speech). Examples is optional.

	etymology
		Text

	ipa
		Pronunciation

	synonyms
		Sequence of strings
	"""


class IDictionaryTermDataStorage(interface.Interface):
	"""
	Stores words and phrases for a dictionary.
	"""

	def lookup( key, exact=False ):
		"""
		Lookup the information about the given word or phrase.
		:return: The :class:`IDictionaryTermData` found for the key
			in this storage, or None.
		"""

class IJsonDictionaryTermDataStorage(interface.Interface):
	"""
	Stores dictionary entries as JSON-encoded strings.
	"""

	def lookup( key, exact=False):
		"""
		Find the JSON string for the term.

		:return: A string containing JSON data representing a dictionary,
			or a special dictionary with a top-level key of 'error'. Note
			that the data may not actually be valid and loadable.
		"""

	def close():
		"""
		"""

class IUncleanJsonDictionaryTermDataStorage(IJsonDictionaryTermDataStorage):
	"""
	The JSON string provided by this object may contain unclean data
	in the ``content`` keys of the ``meanings``.
	"""

class IDictionaryTerm(interface.Interface):
	"""
	A dictionary term that is defined and possibly has additional information associated with it.
	"""

	word = schema.TextLine( title="The defined term",
							description="Not necessarily a word, could also be a phrase." )

	def toXMLString( encoding='UTF-8' ):
		"""
		Write a representation of this object to XML, suitable for use XSLT.

		:param encoding: The name of the encoding to use for the returned string.
			If ``None``, then the returned string will be a unicode object.
		"""

	def addInfo( info ):
		"""
		Adds a detail object providing information about this term.
		"""

	def __iter__( ):
		"""
		Iterates across the info objects added to this term.
		"""
