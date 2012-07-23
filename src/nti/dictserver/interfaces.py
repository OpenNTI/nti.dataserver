#!/usr/bin/env python2.7

from zope import interface

class IJsonDictionary(interface.Interface):
	"""
	"""

	def lookup(word, exact=False):
		"""
		:return: A string containing JSON data representing a dictionary,
			or a special dictionary with a top-level key of 'error'.
		"""

	def close():
		"""
		"""
