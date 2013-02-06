#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.configuration import xmlconfig

import nti.store as store
import nti.dataserver as dataserver

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSSharedConfiguringTestBase

class ConfiguringTestBase(DSSharedConfiguringTestBase):
	set_up_packages = (dataserver, store)
