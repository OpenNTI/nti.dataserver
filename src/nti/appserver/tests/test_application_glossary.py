#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to


from webtest import TestApp

import os.path

import urllib

from nti.ntiids import ntiids

from nti.dataserver.tests import mock_dataserver

import anyjson as json

from .test_application import ApplicationTestBase
from .test_application import PersistentContainedExternal
from .test_application import ContainedExternal

from urllib import quote as UQ

class TestApplicationGlossary(ApplicationTestBase):


	def test_path_with_parens_no_container_no_verify(self):
		"We can hit the glossary of a new container. Does no real verification."
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(tag:NewcontainerResource)/Glossary/demo'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str('xml-stylesheet') ) )
