#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo

from nti.schema.field import TextLine


class ITestSAMLProviderUserInfo(ISAMLProviderUserInfo):
    test_id = TextLine(title=u'text id', required=True)
