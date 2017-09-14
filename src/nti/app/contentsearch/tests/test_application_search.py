#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_string
does_not = is_not

import simplejson as json

from zope import interface

from zope.keyreference.interfaces import IKeyReference

from persistent import Persistent

from nti.coremetadata.mixins import ZContainedMixin

from nti.ntiids.ntiids import TYPE_MEETINGROOM

from nti.ntiids.ntiids import make_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

from nti.app.testing.webtest import TestApp

from nti.dataserver.tests import mock_dataserver


@interface.implementer(IKeyReference)  # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):
    _str = None

    def __str__(self):
        if '_str' in self.__dict__:
            return self._str
        return "<%s %s>" % (self.__class__.__name__, self.to_container_key())

    def toExternalObject(self, **unused_kwargs):
        return str(self)

    def to_container_key(self):
        return to_external_ntiid_oid(self, default_oid=str(id(self)))


class PersistentContainedExternal(ContainedExternal, Persistent):
    pass


class TestApplicationSearch(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_search_empty_term_user_ugd_book(self):

        #"Searching with an empty term returns empty results"
        with mock_dataserver.mock_db_trans(self.ds):
            contained = PersistentContainedExternal()
            user = self._create_user()
            user2 = self._create_user(u'foo@bar')
            user2_username = user2.username
            contained.containerId = make_ntiid(provider=u'OU',
                                               nttype=TYPE_MEETINGROOM,
                                               specific=u'1234')
            user.addContainedObject(contained)
            assert_that(user.getContainer(contained.containerId),
                        has_length(1))

        testapp = TestApp(self.app)
        # The results are not defined across the search types,
        # we just test that it doesn't raise a 404
        for search_path in ('users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData',):
            for ds_path in ('dataserver2',):
                path = '/' + ds_path + '/' + search_path + '/'
                res = testapp.get(path,
                                  extra_environ=self._make_extra_environ())
                assert_that(res.status_int, is_(200))

                # And access is not allowed for a different user
                testapp.get(path,
                            extra_environ=self._make_extra_environ(user=user2_username),
                            status=403)
                # Nor one that doesn't exist
                testapp.get(path,
                            extra_environ=self._make_extra_environ(user='user_dne@biz'),
                            status=401)

    @WithSharedApplicationMockDSWithChanges
    def test_post_share_delete_highlight(self):

        with mock_dataserver.mock_db_trans(self.ds):
            _ = self._create_user()
            self._create_user(username=u'foo@bar')
            testapp = TestApp(self.app)
            containerId = make_ntiid(provider=u'OU',
                                     nttype=TYPE_MEETINGROOM,
                                     specific=u'1234')
            data = json.dumps({
                    'Class': 'Highlight', 
                    'MimeType': 'application/vnd.nextthought.highlight',
                    'ContainerId': containerId,
                    'selectedText': "This is the selected text",
                    'applicableRange': {'Class': 'ContentRangeDescription'}})

        path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
        res = testapp.post(path,
                           data,
                           extra_environ=self._make_extra_environ())
        assert_that(res.status_int, is_(201))
        assert_that(res.body,
                    contains_string('"Class": "ContentRangeDescription"'))
        href = res.json_body['href']
        assert_that(res.headers, 
                    has_entry('Location',
                              contains_string('http://localhost/dataserver2/users/sjohnson@nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID')))
        assert_that(res.headers, 
                    has_entry('Content-Type',
                              contains_string('application/vnd.nextthought.highlight+json')))

        path = '/dataserver2/users/sjohnson@nextthought.com/Pages(%s)/UserGeneratedData' % containerId
        res = testapp.get(path, extra_environ=self._make_extra_environ())
        assert_that(res.body,
                    contains_string('"Class": "ContentRangeDescription"'))

        # I can share the item
        path = href + '/++fields++sharedWith'
        data = json.dumps(['foo@bar'])
        res = testapp.put(str(path),
                          data,
                          extra_environ=self._make_extra_environ())
        assert_that(res.json_body, 
                    has_entry('sharedWith', ['foo@bar']))

        # And the recipient can see it
        path = '/dataserver2/users/foo@bar/Pages(%s)/UserGeneratedData' % containerId
        res = testapp.get(str(path),
                          extra_environ=self._make_extra_environ(user='foo@bar'))
        assert_that(res.body, 
                    contains_string("This is the selected text"))

        # I can now delete that item
        testapp.delete(str(href), 
                       extra_environ=self._make_extra_environ())

        # And it is no longer available
        res = testapp.get(str(path), 
                          extra_environ=self._make_extra_environ(user='foo@bar'),
                          status=404)
