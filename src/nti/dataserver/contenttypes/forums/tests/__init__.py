#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer as DataserverTestLayer
from zope import component
from zope import interface

from zope.keyreference.interfaces import IKeyReference
@interface.implementer(IKeyReference)
class _CommentKeyRef(object):
	def __init__( self, context ):
		pass

class ForumTestLayer(DataserverTestLayer):
	description = 'Forum layer'
	@classmethod
	def setUp(cls):
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
		component.provideUtility( intids, provides=zope.intid.IIntIds )
		# Make sure to register it as both types of utility, one is a subclass of the other
		component.provideUtility( intids, provides=zc.intid.IIntIds )
		cls.__intids = intids


		component.provideAdapter(_CommentKeyRef, adapts=(IPost,))
		component.provideAdapter(_CommentKeyRef, adapts=(IPersonalBlogEntry,) )
		component.provideAdapter(_CommentKeyRef, adapts=(IForum,) )
		component.provideAdapter(_CommentKeyRef, adapts=(ITopic,) )

		from nti.dataserver.tests import mock_redis
		cls.__client = mock_redis.InMemoryMockRedis()
		component.provideUtility( cls.__client )

	@classmethod
	def tearDown(cls):
		gsm = component.getGlobalSiteManager()

		gsm.unregisterUtility(cls.__client)
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
	def testSetUp(cls):
		pass

	@classmethod
	def testTearDown(cls):
		cls.__client.flushall()

class ForumLayerTest(DataserverLayerTest):
	layer = ForumTestLayer
