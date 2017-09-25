#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

from zope.schema.interfaces import TooLong

from nti.chatserver.presenceinfo import PresenceInfo

from nti.chatserver.interfaces import IPresenceInfo

from nti.externalization.externalization import toExternalObject

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class TestPresenceInfo(DataserverLayerTest):

    def test_implements(self):

        info = PresenceInfo()
        assert_that(info, verifiably_provides(IPresenceInfo))

        assert_that(info, validly_provides(IPresenceInfo))

        with self.assertRaises(TooLong):
            info.status = u'foo' * 140  # too big

    def test_construct(self):
        info = PresenceInfo(type=u'unavailable', show=u'away', username=u'me')
        assert_that(info, has_property('type', 'unavailable'))
        assert_that(info, has_property('show', 'away'))
        assert_that(info, has_property('username', 'me'))

    def test_externalizes(self):
        info = PresenceInfo()
        assert_that(info, 
					externalizes(has_entries('show', 'chat', 'status', '', 
											 'type', 'available',
                                             'Class', 'PresenceInfo', 
                                             'MimeType', 'application/vnd.nextthought.presenceinfo')))

        factory = find_factory_for(toExternalObject(info))
        assert_that(factory, is_not(none()))
        assert_that(list(factory.getInterfaces()),
                    has_item(IPresenceInfo))

        update_from_external_object(info, 
									{'status': u'My status', 'Last Modified': 1234})
        assert_that(info.status, is_('My status'))
        assert_that(info.lastModified, is_(1234))
        assert_that(info, validly_provides(IPresenceInfo))
