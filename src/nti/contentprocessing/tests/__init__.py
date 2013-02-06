#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.contentprocessing as contentprocessing
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, contentprocessing)
