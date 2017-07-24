#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import unittest

from nti.app.contentfolder.adapters import S3FileIO

from nti.contentfile.interfaces import IS3FileIO

from nti.contentfile.model import S3File

from nti.contentfolder.boto_s3 import is_boto_available

from nti.contentfolder.model import S3RootFolder

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


@unittest.skipUnless(is_boto_available(), "Boto keys/bucket not set")
class TestBotoS3(ApplicationLayerTest):
    
    @WithSharedApplicationMockDS(users=False, testapp=False)
    def test_s3file(self):
        
        with mock_dataserver.mock_db_trans(self.ds):
            root = self.ds.root['bleach'] = S3RootFolder(name='bleach')
            ichigo = S3File('kurosaki', 'text/plain', 'ichigo')
            root[ichigo.name] = ichigo
        
        with mock_dataserver.mock_db_trans(self.ds):
            ichigo = self.ds.root['bleach']['ichigo']
            s3 = IS3FileIO(ichigo)
            assert_that(s3.key(), is_('ichigo'))
            assert_that(s3.exists(), is_(True))
            assert_that(s3.contents(), is_('kurosaki'))
            assert_that(s3.size(), is_(8))

        with mock_dataserver.mock_db_trans(self.ds):
            ichigo = self.ds.root['bleach']['ichigo']
            assert_that(ichigo, has_property('data', is_('kurosaki')))
            ichigo.data = 'zangetsu'
        
        with mock_dataserver.mock_db_trans(self.ds):
            ichigo = self.ds.root['bleach']['ichigo']
            assert_that(ichigo, has_property('data', is_('zangetsu')))
            del self.ds.root['bleach']['ichigo']

        s3 = S3FileIO()
        assert_that(s3.exists('ichigo'), is_(False))
