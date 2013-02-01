from __future__ import unicode_literals, print_function, absolute_import

from zope import component
from zope.configuration import xmlconfig

import nti.store as store
import nti.dataserver as dataserver

from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, store)
		