#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: test_forum.py 21359 2013-07-26 05:23:32Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import component

from nti.externalization.externalization import toExternalObject

from ..interfaces import IForumACE
from ..interfaces import IACLCommunityForum

from .._ace import ForumACE
from ..forum import ACLCommunityForum

import nti.tests
from nti.tests import verifiably_provides, validly_provides

from hamcrest import (assert_that, has_length, has_entry, has_entries)

def setUpModule():
	nti.tests.module_setup(set_up_packages=(('subscribers.zcml', 'nti.intid'),
											 'nti.dataserver.contenttypes.forums',
											 'nti.contentfragments',
											 'zope.annotation',))

	from nti.dataserver.tests import mock_redis
	client = mock_redis.InMemoryMockRedis()
	component.provideUtility(client)

tearDownModule = nti.tests.module_teardown


def test_acl_forum_interfaces():
	forum = ACLCommunityForum()
	assert_that(forum, verifiably_provides(IACLCommunityForum))
	assert_that(forum, validly_provides(IACLCommunityForum))

def test_forum_ace_interfaces():
	ace = ForumACE()
	assert_that(ace, verifiably_provides(IForumACE))

def test_externalizes():
	ace = ForumACE(Action='Allow', Permission='All', Entities=('foo',))
	forum = ACLCommunityForum()
	forum.ACL = [ace]
	external = toExternalObject(forum)
	assert_that(external, has_entry('ACL', has_length(1)))
	assert_that(external['ACL'][0], 
				has_entries('Action', u'Allow',
          					'Class','ACE',
          	    			'Entities', [u'foo'],
         		 	     	'MimeType', 'application/vnd.nextthought.forumace',
          		 	     	'Permission','All'))
