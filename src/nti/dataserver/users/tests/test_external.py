#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.auto_subscribe import SiteAutoSubscribeMembershipPredicate

from nti.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization import update_from_external_object


class TestExternal(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_auto_subscribe(self):
        obj = SiteAutoSubscribeMembershipPredicate()
        ext = to_external_object(obj)
        assert_that(ext, has_entry('Class', 'SiteAutoSubscribeMembershipPredicate'))
        assert_that(ext,
                    has_entry('MimeType', SiteAutoSubscribeMembershipPredicate.mime_type))
        assert_that(ext, has_entry('Last Modified', is_not(none())))

        factory = find_factory_for(ext)
        new_obj = factory()

        update_from_external_object(new_obj, ext)
        assert_that(new_obj, has_property(u'mimeType', SiteAutoSubscribeMembershipPredicate.mime_type))
