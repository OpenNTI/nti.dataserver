#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

try:
	from saml2.s2repoze.plugins.sp import SAML2Plugin as _SAML2Plugin
except ImportError: # pypy
	_SAML2Plugin = None

def create_saml2_plugin():
	
	if _SAML2Plugin is None:
		return None

	class SAML2Plugin(_SAML2Plugin):
		pass
