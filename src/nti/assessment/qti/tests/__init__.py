#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# This layer MUST NOT have a dependency on the dataserver
#from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSSharedConfiguringTestBase
from nti.tests import SharedConfiguringTestBase

class ConfiguringTestBase(SharedConfiguringTestBase):
	set_up_packages = ('nti.assessment.qti',)
