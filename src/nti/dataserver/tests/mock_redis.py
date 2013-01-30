#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import this module to access a mock redis implementation named `InMemoryMockRedis`.
Prefer importing this module over directly importing :mod:`fakeredis`
so that the proper cleanups are established.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
import zope.testing.cleanup

from nti.dataserver import interfaces as nti_interfaces

import fakeredis

interface.classImplements( fakeredis.FakeStrictRedis, nti_interfaces.IRedisClient )
zope.testing.cleanup.addCleanUp( fakeredis.DATABASES.clear )

InMemoryMockRedis = fakeredis.FakeStrictRedis # BWC alias

if not hasattr( InMemoryMockRedis, 'pubsub' ):
	# Nark. No pub sub support. Hack in some
	# basic stuff
	class PubSub(object):
		def subscribe(self, channel):
			pass
		def listen(self):
			return ()

	InMemoryMockRedis.publish = lambda s, c, m: None
