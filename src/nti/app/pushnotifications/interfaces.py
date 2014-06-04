#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope.viewlet.interfaces import IViewletManager


class INotableDataEmailViewletManager(IViewletManager):
	"""
	Viewlet manager for notable data items in the push email.

	This should be a ``ConditionalViewletManager`` to support
	ordering and conditional inclusion of rows.
	"""
