#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import nti.dataserver as dataserver

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSSharedConfiguringTestBase

class ConfiguringTestBase(DSSharedConfiguringTestBase):
	set_up_packages = (dataserver,)
