# -*- coding: utf-8 -*-
"""
Stemmer interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

class IStemmer(interface.Interface):

	def stem(token):
		"""
		Return the stem of the specified token
		"""
