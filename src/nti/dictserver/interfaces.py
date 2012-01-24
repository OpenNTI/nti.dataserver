#!/usr/bin/env python2.7

from zope import interface

class IDictionary(interface.Interface):
	"""
	"""

	def lookup(word, exact=False):
		"""
		"""

	def close():
		"""
		"""
