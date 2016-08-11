#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

try:
	from saml2.s2repoze.plugins.sp import SAML2Plugin
except ImportError: # pypy
	SAML2Plugin = object

class NTISAML2Plugin(SAML2Plugin):
	pass

def create_saml2_plugin():
	if SAML2Plugin is object:
		return None
	else:
		pass
