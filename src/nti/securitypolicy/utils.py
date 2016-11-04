#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def is_impersonating(request):
	# We know we are impersonating if we have a 'REMOTE_USER_DATA'
	# value in the environ
	environ = getattr(request, 'environ', ())
	return bool('REMOTE_USER_DATA' in environ and environ['REMOTE_USER_DATA'])
