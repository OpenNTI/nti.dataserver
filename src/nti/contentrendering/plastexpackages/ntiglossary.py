#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command

# SAJ: The logic of the glossary entry is derived from that of the footnote.
class ntiglossaryentry(Command):
	mark = None
	args = 'entryname self'

	def invoke(self, tex):
		# Add the glossary entry to the document
		output = Command.invoke(self, tex)
		userdata = self.ownerDocument.userdata
		if 'glossary' not in userdata:
			userdata['glossary'] = []
		userdata['glossary'].append(self)
		self.mark = self
		return output
