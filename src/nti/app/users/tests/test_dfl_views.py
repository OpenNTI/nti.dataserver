#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_item
from hamcrest import ends_with
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

from six.moves import urllib_parse

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.app.users.views.dfl_views import REL_MY_MEMBERSHIP

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.users import User


class TestApplicationDFLViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_link_in_dfl(self):

        with mock_dataserver.mock_db_trans(self.ds):
            owner = self._create_user()
            owner_username = owner.username
            member_user = self._create_user(u'member@foo')
            member_user_username = member_user.username
            other_user = self._create_user(u'otheruser@foo')
            other_user_username = other_user.username

            fl1 = DynamicFriendsList(username=u'Friends')
            fl1.creator = owner  # Creator must be set
            owner.addContainedObject(fl1)
            fl1.addFriend(member_user)
            fl1.addFriend(other_user)

            assert_that(member_user.entities_followed, contains(fl1))

            dfl_ntiid = fl1.NTIID
            fl1_containerId = fl1.containerId
            fl1_id = fl1.id

        # pylint: disable=no-member
        testapp = TestApp(self.app)

        # The member is the only one that has the link
        path = '/dataserver2/Objects/' + dfl_ntiid
        path = str(path)
        path = urllib_parse.quote(path)

        res = testapp.get(path,
                          extra_environ=self._make_extra_environ(member_user_username))
        assert_that(res.json_body,
                    has_entry('Links', has_item(has_entries('rel', REL_MY_MEMBERSHIP,
                                                            'href', ends_with('/@@' + REL_MY_MEMBERSHIP)))))

        res = testapp.get(path, extra_environ=self._make_extra_environ())
        assert_that(res.json_body['Links'],
                    does_not(has_item(has_entry('rel', REL_MY_MEMBERSHIP))))

        # And the member can delete it, once
        testapp.delete(path + '/@@' + str(REL_MY_MEMBERSHIP),
                       extra_environ=self._make_extra_environ(username=member_user_username))

        # after which it 404s
        testapp.delete(path + '/@@' + str(REL_MY_MEMBERSHIP),
                       extra_environ=self._make_extra_environ(
                           username=member_user_username),
                       status=404)

        # The member is no longer a member and no longer follows
        with mock_dataserver.mock_db_trans(self.ds):
            owner = User.get_user(owner_username)
            member_user = User.get_user(member_user_username)
            other_user = User.get_user(other_user_username)
            dfl = owner.getContainedObject(fl1_containerId, fl1_id)
            assert_that(list(dfl), is_([other_user]))
            assert_that(member_user.entities_followed, does_not(contains(dfl)))

    @WithSharedApplicationMockDS
    def test_dfl_links(self):

        with mock_dataserver.mock_db_trans(self.ds):
            owner = self._create_user()
            owner_username = owner.username
            member_username = u'member@foo'
            member_user = self._create_user(member_username)
            other_user = self._create_user(u'otheruser@foo')
            non_member_username = u'nonmember@foo'
            self._create_user(non_member_username)

            fl1 = DynamicFriendsList(username=u'Friends')
            fl1.creator = owner  # Creator must be set
            owner.addContainedObject(fl1)
            fl1.addFriend(member_user)
            fl1.addFriend(other_user)
            fl1.Locked = True

            dfl_ntiid = fl1.NTIID

        # pylint: disable=no-member
        testapp = TestApp(self.app)

        path = '/dataserver2/Objects/' + dfl_ntiid
        path = str(path)
        path = urllib_parse.quote(path)

        # Owner
        res = testapp.get(path,
                          extra_environ=self._make_extra_environ(owner_username))
        assert_that(res.json_body, has_entry('Links',
                                             does_not(has_item(has_entries('rel', 'edit')))))

        assert_that(res.json_body, has_entry('Links',
                                             has_item(has_entries('rel', 'Activity'))))

        assert_that(res.json_body, has_entry('Links',
                                             has_item(has_entries('rel', 'SuggestedContacts'))))

        # Member
        res = testapp.get(path,
                          extra_environ=self._make_extra_environ(member_username))
        assert_that(res.json_body, has_entry('Links',
                                             does_not(has_item(has_entries('rel', 'edit')))))

        assert_that(res.json_body, has_entry('Links',
                                             has_item(has_entries('rel', 'Activity'))))

        assert_that(res.json_body, has_entry('Links',
                                             has_item(has_entries('rel', 'SuggestedContacts'))))

    @WithSharedApplicationMockDS
    def test_activity_dfl(self):

        with mock_dataserver.mock_db_trans(self.ds):
            owner = self._create_user()
            owner_username = owner.username
            ichigo = self._create_user(u'ichigo')
            aizen = self._create_user(u'aizen')
            self._create_user(u'rukia')

            dfl = DynamicFriendsList(username=u'Friends')
            dfl.creator = owner  # Creator must be set
            owner.addContainedObject(dfl)
            dfl.addFriend(ichigo)
            dfl.addFriend(aizen)
            dfl_ntiid = dfl.NTIID

            note = Note()
            note.body = [u'bankai']
            note.creator = owner
            note.addSharingTarget(dfl)
            note.containerId = u'mycontainer'
            owner.addContainedObject(note)

        path = '/dataserver2/Objects/%s/Activity' % dfl_ntiid
        # pylint: disable=no-member
        testapp = TestApp(self.app)
        path = urllib_parse.quote(str(path))

        res = testapp.get(path,
                          extra_environ=self._make_extra_environ(owner_username))
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        res = testapp.get(path,
                          extra_environ=self._make_extra_environ('ichigo'))
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        testapp.get(path,
                    extra_environ=self._make_extra_environ('rukia'), status=403)

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_list_dfls(self):

        with mock_dataserver.mock_db_trans(self.ds):
            ichigo = self._create_user(u'ichigo')
            aizen = self._create_user(u'aizen')
            self._create_user(u'rukia')

            dfl = DynamicFriendsList(username=u'Friends')
            dfl.creator = ichigo  # Creator must be set
            ichigo.addContainedObject(dfl)
            dfl.addFriend(aizen)

        path = '/dataserver2/@@list_dfls'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))
