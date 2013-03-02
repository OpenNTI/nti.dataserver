#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.contentprocessing as contentprocessing

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, contentprocessing)
