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
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import same_instance
from nose.tools import assert_raises
import nti.tests

from ..singleton import SingletonDecorator

def test_singleton_decorator():

	class X(object):
		__metaclass__ = SingletonDecorator


	# No context
	assert_that( X(), is_( same_instance( X() ) ) )

	# context ignored
	assert_that( X('context'), is_( same_instance( X('other_context') ) ) )

	# two contexts for the common multi-adapter case
	assert_that( X('context', 'request'), is_( same_instance( X('other_context', 'other_request') ) ) )

	x = X()
	with assert_raises(AttributeError):
		x.b = 1

	with assert_raises(AttributeError):
		getattr( x, '__dict__' )
