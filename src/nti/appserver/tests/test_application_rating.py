#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that

import urllib
import anyjson as json

from nti.contentrange import contentrange

from nti.dataserver import contenttypes

from nti.ntiids.oids import to_external_ntiid_oid

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.dataserver.tests import mock_dataserver


class TestApplicationRating(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_rate_note(self):

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user()
            n = contenttypes.Note()
            n.applicableRange = contentrange.ContentRangeDescription()
            n.containerId = u'tag:nti:foo'
            user.addContainedObject(n)
            n_ext_id = to_external_ntiid_oid(n)

        testapp = TestApp(self.app)
        path = '/dataserver2/Objects/%s' % n_ext_id
        path = urllib.quote(path)

        res = testapp.get(path, extra_environ=self._make_extra_environ())
        assert_that(res.status_int, is_(200))

        assert_that(res.json_body, is_not(has_key('Rating')))
        assert_that(json.loads(res.body), 
                    has_entry('Links', has_item(has_entry('rel', 'rate'))))
        assert_that(json.loads(res.body),
                    has_entry('Links',
                              has_item(
                                  has_entry(
                                      'href',
                                      '/dataserver2/Objects/' + urllib.quote(n_ext_id) + '/@@rate'))))

        # So I do
        data = json.dumps({'rating': 4})
        res = testapp.post(path + '/@@rate', data,
                           extra_environ=self._make_extra_environ())
        # and now I'm asked to unlike
        assert_that(res.status_int, is_(200))
        assert_that(res.json_body, has_entry('Rating', 4))
        assert_that(res.json_body, 
                    has_entry('Links', has_item(has_entry('rel', 'unrate'))))

        # Same again
        data = json.dumps({'rating': 3})
        res = testapp.post(path + '/@@rate', data,
                           extra_environ=self._make_extra_environ())
        assert_that(res.status_int, is_(200))
        assert_that(res.json_body, has_entry('Rating', 3))
        assert_that(res.json_body, 
                    has_entry('Links', has_item(has_entry('rel', 'unrate'))))

        # And I can unrate
        res = testapp.delete(path + '/@@unrate',
                             extra_environ=self._make_extra_environ())
        assert_that(res.status_int, is_(200))
        assert_that(res.json_body, is_not(has_key('Rating')))
        assert_that(res.json_body, 
                    has_entry('Links', has_item(has_entry('rel', 'rate'))))
