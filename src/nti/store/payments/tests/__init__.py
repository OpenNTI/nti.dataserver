from __future__ import unicode_literals, print_function, absolute_import

from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.store.payments as payments
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, payments)
		
