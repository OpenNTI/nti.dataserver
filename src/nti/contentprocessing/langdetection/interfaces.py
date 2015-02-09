#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Language detection interfaces

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import ValidTextLine

class ILanguage(interface.Interface):
	"""
	represent a language
	"""
	code = ValidTextLine(title="language iso-639-1 code", required=True)
	name = ValidTextLine(title="language name", required=False)

class IAlchemyLanguage(ILanguage):
	"""
	represent a language
	"""
	ISO_639_1 = ValidTextLine(title="language iso-639-1 code", required=True)  # alias for code
	ISO_639_2 = ValidTextLine(title="language iso-639-2 code", required=False)
	ISO_639_3 = ValidTextLine(title="language iso-639-3 code", required=False)
	name = ValidTextLine(title="language name", required=False)

class ILanguageDetector(interface.Interface):

	def __call___(content):
		"""
		Return an ILanguage(s) associated with the specified content
		
		:param content: Text to process
		"""
