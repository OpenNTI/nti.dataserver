#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests
from nti.tests import aq_inContextOf
try:
	from zope.proxy import ProxyBase
except ImportError:
	ProxyBase = lambda x: x

try:
	from zope.container.contained import ContainedProxy
except ImportError:
	ContainedProxy = lambda x: x

try:
	from Acquisition import Implicit
	from ExtensionClass import Base
	class EC(Base):
		x = None
	class IM(Implicit):
		pass
	def aq_proxied(im):
		ec = EC()
		ec.x = im
		assert_that( ec.x, is_( aq_inContextOf( ec ) ) )
		return ec.x


except ImportError:
	EC = None
	class IM(object):
		pass
	def aq_proxied():
		return IM()


from ..proxy import removeAllProxies
def test_removeAllProxies():

	obj = IM()

	# One layer of wrapping of each
	for wrap in ProxyBase, ContainedProxy, aq_proxied:
		wrapped = wrap( obj )
		assert_that( removeAllProxies( wrapped ), is_( same_instance( obj ) ) )

	# double wrapping in weird combos
	for wrap in ProxyBase, ContainedProxy, aq_proxied:
		wrapped = wrap( obj )
		for wrap2 in ContainedProxy, ProxyBase:
			__traceback_info__ = wrap, wrap2
			wrapped = wrap2( wrapped )
			assert_that( removeAllProxies( wrapped ), is_( same_instance( obj ) ) )
