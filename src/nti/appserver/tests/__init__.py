import nti.appserver

import zope.deferredimport
zope.deferredimport.initialize()


import nti.deprecated # Increase warning verbosity
assert nti.deprecated
from nti.app.testing.request_response import DummyRequest
from nti.app.testing.testing import TestMailDelivery
from nti.app.testing.testing import ITestMailDelivery


from nti.app.testing.matchers import has_permission as _has_permission
from nti.app.testing.matchers import doesnt_have_permission as _doesnt_have_permission

from nti.app.testing.base import _create_request
_create_request = _create_request
from nti.app.testing.base import TestBaseMixin
_TestBaseMixin = TestBaseMixin
from nti.app.testing.base import ConfiguringTestBase
ConfiguringTestBase = ConfiguringTestBase
from nti.app.testing.base import SharedConfiguringTestBase
SharedConfiguringTestBase = SharedConfiguringTestBase
from nti.app.testing.base import NewRequestSharedConfiguringTestBase
NewRequestSharedConfiguringTestBase = NewRequestSharedConfiguringTestBase
