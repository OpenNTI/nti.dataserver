#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: interfaces.py 97349 2016-09-23 18:37:47Z bobby.hagen $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo

from nti.schema.field import TextLine

class ITestSAMLProviderUserInfo(ISAMLProviderUserInfo):
	test_id = TextLine(title='text id', required=True)
