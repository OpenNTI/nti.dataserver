#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

import time

from hamcrest import is_
from hamcrest import none
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import contains_string
from hamcrest import contains_inanyorder

from six.moves.urllib_parse import quote

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.users import User
from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.ntiids.oids import to_external_ntiid_oid


class Test_FriendsListsFriendsFieldUpdateView(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user002', u'user003', u'user004'), testapp=True, default_authenticate=False)
    def test_post_friendslist_friends_field(self):
        #"We can put to ++fields++friends"
        with mock_dataserver.mock_db_trans( self.ds ):
            self._create_user('troy.daley@nextthought.com')

        # Make one
        data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["steve.johnson@nextthought.com"],"realname":"boom"}'
        path = '/dataserver2/users/sjohnson@nextthought.com'
        res = self.testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )

        now = time.time()

        # Edit it
        data = '["troy.daley@nextthought.com"]'
        path = res.json_body['href'] + '/++fields++friends'

        res = self.testapp.put( str(path),
                           data,
                           extra_environ=self._make_extra_environ(),
                           headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
        assert_that( res.status_int, is_( 200 ) )
        assert_that( res.json_body, has_entry( 'friends', has_item( has_entry( 'Username', 'troy.daley@nextthought.com' ) ) ) )
        assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

        # the object itself is uncachable as far as HTTP goes
        assert_that( res, has_property( 'last_modified', none() ) )
        # But the last modified value is preserved in the body, and did update
        # when we PUT
        assert_that( res.json_body, has_entry( 'Last Modified', greater_than( now ) ) )

        # We can fetch the object and get the same info
        last_mod = res.json_body['Last Modified']
        href = res.json_body['href']

        res = self.testapp.get( href, extra_environ=self._make_extra_environ() )
        assert_that( res.status_int, is_( 200 ) )
        assert_that( res.json_body, has_entries( 'Last Modified', last_mod, 'href', href ) )

        # And likewise for the collection
        res = self.testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
        assert_that( res.status_int, is_( 200 ) )
        assert_that( res.json_body['Items'], has_entry( 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-MeetingRoom:Group-boom@nextthought.com',
                                                        has_entries( 'Last Modified', last_mod,
                                                                     'href', href ) ) )
        # additions/removals
        data = {
            'additions': ['user002', 'user003', 'user004'],
            'removals': ['user003']
        }
        result = self.testapp.put_json(str(path), data, extra_environ=self._make_extra_environ()).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user002','user004',"troy.daley@nextthought.com"))

    @WithSharedApplicationMockDS(users=(u'user001', u'user002', u'user003', u'user004'), testapp=True, default_authenticate=False)
    def test_dynamic_friends_list(self):
        owner = u'user001'
        owner_environ = self._make_extra_environ(user=owner)
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(owner)

            dfl = DynamicFriendsList(username=u'dfl001')
            dfl.creator = user
            user.addContainedObject(dfl)

            groupNTIID = dfl.NTIID

        url = '/dataserver2/NTIIDs/%s/++fields++friends' % groupNTIID

        # friends
        data = ['user001', 'user002', 'user003', 'userxxx']
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(2))

        data = []
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(0))

        # additions
        data = { 'additions': ['user001', 'user002', 'user003'] }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user002', 'user003'))

        # removals
        data = {'removals': None}
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(2))

        data = {'removals': []}
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(2))

        data = { 'removals': ['user002', 'user003', 'user004'] }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(0))

        data = { 'removals': ['user002', 'user003', 'user004'] }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that(result['friends'], has_length(0))

        # additions/removals
        data = {
            'additions': ['user002', 'user003', 'user004'],
            'removals': ['user002', 'user004', 'userxxx']
        }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user003'))

        # user003 appears in both additions/removals, ignored.
        data = {
            'additions': ['user003', 'user004'],
            'removals': ['user002', 'user003']
        }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user003','user004'))

        # no additions/removals, keep unchanged.
        data = { 'additions': None, 'removals': None }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user003', 'user004'))

        # no user found
        data = { 'additions': ['xxx'], 'removals': ['yyy'] }
        result = self.testapp.put_json(url, data, extra_environ=owner_environ, status=200).json_body
        assert_that([x['Username'] for x in result['friends']], contains_inanyorder('user003', 'user004'))
