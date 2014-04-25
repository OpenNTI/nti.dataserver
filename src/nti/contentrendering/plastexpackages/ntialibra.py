#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alibra macros

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Base

from ._util import LocalContentMixin

class ntiheader(LocalContentMixin, Base.Environment):
	pass

class ntisequenceitem(LocalContentMixin, Base.List.item):
	pass

class ntisequence(LocalContentMixin, Base.List):
	args = '[options:dict]'

	def digest(self, tokens):
		result = super(ntisequence, self).digest(tokens)
		if self.macroMode != Base.Environment.MODE_END:

			_ntiheader = self.getElementsByTagName('ntiheader')
			assert len(_ntiheader) <= 1

			_items = self.getElementsByTagName('ntisequenceitem')
			assert len(_items) >= 1

		return result

class ntisequenceref(Base.Crossref.ref):
	
	args = '[options:dict] label:idref'

	def digest(self, tokens):
		tok = super(ntisequenceref, self).digest(tokens)
		return tok
