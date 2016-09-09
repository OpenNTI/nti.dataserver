#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component
from zope import interface

from zope.keyreference.interfaces import IKeyReference

from nti.dataserver.interfaces import IRedisClient

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer as DataserverTestLayer

@interface.implementer(IKeyReference)
class _CommentKeyRef(object):
	def __init__( self, context ):
		pass

class ForumTestLayer(DataserverTestLayer):

	@classmethod
	def setUp(cls):
		gsm = component.getGlobalSiteManager()

		# Set up weak refs
		from nti.intid import utility as intid_utility
		import zope.intid
		import zc.intid
		import BTrees

		from ..interfaces import IPost
		from ..interfaces import IPersonalBlogEntry
		from ..interfaces import IForum
		from ..interfaces import ITopic

		intids = intid_utility.IntIds('_ds_intid', family=BTrees.family64 )
		intids.__name__ = '++etc++intids'
		gsm.registerUtility( intids, provided=zope.intid.IIntIds )
		# Make sure to register it as both types of utility, one is a subclass of the other
		gsm.registerUtility( intids, provided=zc.intid.IIntIds )
		cls.__intids = intids

		gsm.registerAdapter(_CommentKeyRef, required=(IPost,))
		gsm.registerAdapter(_CommentKeyRef, required=(IPersonalBlogEntry,) )
		gsm.registerAdapter(_CommentKeyRef, required=(IForum,) )
		gsm.registerAdapter(_CommentKeyRef, required=(ITopic,) )

		from nti.dataserver.tests import mock_redis
		cls.__client = mock_redis.InMemoryMockRedis()
		gsm.registerUtility( cls.__client, provided=IRedisClient )

		assert component.getUtility(IRedisClient) is cls.__client

	@classmethod
	def tearDown(cls):
		gsm = component.getGlobalSiteManager()

		gsm.unregisterUtility(cls.__client, provided=IRedisClient)
		del cls.__client

		import zope.intid
		import zc.intid

		gsm.unregisterUtility(cls.__intids, provided=zope.intid.IIntIds )
		gsm.unregisterUtility(cls.__intids, provided=zc.intid.IIntIds )
		del cls.__intids

		from ..interfaces import IPost
		from ..interfaces import IPersonalBlogEntry
		from ..interfaces import IForum
		from ..interfaces import ITopic

		gsm.unregisterAdapter(_CommentKeyRef, required=(IPost,))
		gsm.unregisterAdapter(_CommentKeyRef, required=(IPersonalBlogEntry,) )
		gsm.unregisterAdapter(_CommentKeyRef, required=(IForum,) )
		gsm.unregisterAdapter(_CommentKeyRef, required=(ITopic,) )

	@classmethod
	def testSetUp(cls, test=None):
		pass

	@classmethod
	def testTearDown(cls):
		cls.__client.flushall()

class ForumLayerTest(DataserverLayerTest):
	layer = ForumTestLayer
