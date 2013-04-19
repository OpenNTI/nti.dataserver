#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import nti.store as store
import nti.appserver as appserver
import nti.dataserver as dataserver

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSSharedConfiguringTestBase

class ConfiguringTestBase(DSSharedConfiguringTestBase):
	set_up_packages = (dataserver, store, ('configure_invitations.zcml', appserver)) + (('purchasables.zcml', 'nti.store.tests'),)
