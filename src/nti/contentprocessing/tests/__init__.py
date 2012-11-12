from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.contentprocessing as contentprocessing
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, contentprocessing)
		
