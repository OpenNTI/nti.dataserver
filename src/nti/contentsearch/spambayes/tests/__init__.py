from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.contentsearch as contentsearch
import nti.contentsearch.spambayes as spambayes

from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase as DSConfiguringTestBase

class ConfiguringTestBase(DSConfiguringTestBase):
    set_up_packages = (dataserver, contentsearch, spambayes)