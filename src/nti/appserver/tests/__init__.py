import nti.appserver

import zope.deferredimport
zope.deferredimport.initialize()

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from nti.testing.base import ConfiguringTestBase as _ConfiguringTestBase
from nti.testing.base import SharedConfiguringTestBase as _SharedConfiguringTestBase

import nti.deprecated # Increase warning verbosity
assert nti.deprecated
from nti.app.testing.request_response import DummyRequest
from nti.app.testing.testing import TestMailDelivery
from nti.app.testing.testing import ITestMailDelivery


_old_pw_manager = None
def setUpPackage():
	from nti.dataserver.users import Principal
	global _old_pw_manager
	# By switching from the very secure and very expensive
	# bcrypt default, we speed application-level tests
	# up (due to faster principal creation and faster password authentication)
	# The forum tests go from 55s to 15s
	# This is a nose1 feature and will have to be moved for nose2,
	# probably to layers (which is a good thing in general)
	_old_pw_manager = Principal.password_manager_name
	Principal.password_manager_name = 'Plain Text'

def tearDownPackage():
	if _old_pw_manager:
		from nti.dataserver.users import Principal
		Principal.password_manager_name = _old_pw_manager

import pyramid.interfaces


import zope.component as component

from nti.dataserver.tests import mock_dataserver
import nti.testing.base



import webtest.app
import webtest.utils


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
