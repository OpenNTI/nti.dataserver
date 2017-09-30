#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo

from nti.schema.field import TextLine


class ITestSAMLProviderUserInfo(ISAMLProviderUserInfo):
    test_id = TextLine(title=u'text id', required=True)
