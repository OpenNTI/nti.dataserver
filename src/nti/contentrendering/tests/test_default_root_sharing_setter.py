#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id$

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import not_none

from . import ConfiguringTestBase
from nti.contentrendering import RenderedBook
from nti.contentrendering import default_root_sharing_setter
from nti.tests import verifiably_provides
from nti.contentrendering import interfaces
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook

import io
import os
import platform
is_pypy = platform.python_implementation() == 'PyPy'
from unittest import skipIf


TEST_CONTENT = 'NextThoughtGenericTutorial-rendered-book'

def _resource( name ):
	return os.path.join( os.path.dirname( __file__ ), name )

def test_module_provides():
	assert_that( default_root_sharing_setter, verifiably_provides(interfaces.IRenderedBookTransformer ) )

class TestTransforms(ConfiguringTestBase):

	def test_file_sharedWith(self):
		"""
		Verify that defaultsharingsetter can read the default sharing info from the designated file and
		update the ToC.
		"""

		# Read the reference data
		lines = io.open( _resource( 'nti-default-root-sharing-group.txt' ), encoding='utf-8' ).readlines()
		refData = ' '.join( (line.strip() for line in lines) ).strip()

		# Open the copy of the rendered book
		book = NoConcurrentPhantomRenderedBook( None, _resource( TEST_CONTENT ) )

		# Assert ToC is present
		assert_that( book, has_property( 'toc', not_none() ) )
		# Assert that the root topic is present
		assert_that( book.toc, has_property( 'root_topic', not_none() ) )

		default_root_sharing_setter.transform( book, save_toc=False )

		# Assert that the shareWith property of the ToC root element is set correctly
		assert_that( book.toc.root_topic.get_default_sharing_group(), is_( refData ) )

	def test_arg_sharedWith(self):
		"""
		Verify that defaultsharingsetter can read the default sharing info from the command line and
		update the ToC.
		"""

		# Read the reference data
		refData = 'entity0 entity1 entity2 entity3'

		# Open the copy of the rendered book
		book = NoConcurrentPhantomRenderedBook( None, _resource( TEST_CONTENT ) )

		# Assert ToC is present
		assert_that( book, has_property( 'toc', not_none() ) )
		# Assert that the root topic is present
		assert_that( book.toc, has_property( 'root_topic', not_none() ) )

		default_root_sharing_setter.transform( book, save_toc=False, group_name=refData )

		# Assert that the shareWith property of the ToC root element is set correctly
		assert_that( book.toc.root_topic.get_default_sharing_group(), is_( refData ) )
