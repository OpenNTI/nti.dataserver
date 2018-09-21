#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import is_

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.appserver.policies.object_io import SitePolicyUserEventListenerObjectIO

from nti.appserver.policies.site_policies import AdultCommunitySitePolicyEventListener

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestObjectIO(ApplicationLayerTest):

    def test_generic_site_policy(self):
        policy = AdultCommunitySitePolicyEventListener()
        policy_io = SitePolicyUserEventListenerObjectIO(policy)
        ext_policy = policy_io.toExternalObject()
        attrs = [attr for attr in dir(policy) if attr.isupper()]
        for attr in attrs:
            assert_that(getattr(policy, attr), is_(ext_policy.get(attr)))
        from IPython.terminal.debugger import set_trace;set_trace()

        ext_policy['COM_USERNAME'] = u'xyz'
        policy_io.updateFromExternalObject(ext_policy)
        assert_that(policy.COM_USERNAME, is_(u'xyz'))
