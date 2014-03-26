#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces used during bulk email processing.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

class IBulkEmailProcessLoop(interface.Interface):
	"""
	Something that implements the processing algorithem
	defined in this package.

	For now, the only supported way to provide an implementation of this
	interface is to subclass the provided value; this will become more pluggable.

	Implementations should be registered as named adapters
	from the request; their name is the name of the subpath used to get to them.
	(NOTE: This could/should be much more flexible using traversal.)
	"""
