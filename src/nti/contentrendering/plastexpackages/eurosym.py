# -*- coding: utf-8 -*-
"""
Define the Eurosym package

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command
from plasTeX.DOM import Text

class eur(Command):
	args = 'self'
	macroName = 'EUR'

	def invoke(self, tex):
		super(eur, self).invoke(tex)
		node = Text(u'\u20AC\u202F')
		self.attributes['self'].childNodes.insert(0, node)

class euro(Command):
	unicode = u'\u20AC'

