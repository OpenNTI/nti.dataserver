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
from nti.contentfolder.model import S3ContentFolder

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

    @WithSharedApplicationMockDS(users=False, testapp=False)
    def test_s3folder(self):

        # add folder
        with mock_dataserver.mock_db_trans(self.ds):
            root = self.ds.root['bleach'] = S3RootFolder(name='bleach')
            bankai = S3ContentFolder(name='bankai')
            root.append(bankai)

        # test added folder
        with mock_dataserver.mock_db_trans(self.ds):
            bankai = self.ds.root['bleach']['bankai']
            s3 = IS3FileIO(bankai)
            assert_that(s3.key(), is_('bankai/'))
            assert_that(s3.exists(), is_(True))
            assert_that(s3.contents(), is_(''))
            assert_that(s3.size(), is_(0))

        # add file
        with mock_dataserver.mock_db_trans(self.ds):
            bankai = self.ds.root['bleach']['bankai']
            ichigo = S3File('zangetsu', 'text/plain', 'ichigo')
            bankai.add(ichigo)

        # test added file
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            bankai = bleach['bankai']
            ichigo = bankai['ichigo']
            assert_that(ichigo, has_property('data', is_('zangetsu')))
            s3 = IS3FileIO(ichigo)
            assert_that(s3.key(), is_('bankai/ichigo'))

        # add some samples
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            shikai = S3ContentFolder(name='chikai')
            bleach.append(shikai)
            izuru = S3File('wabisuke', 'text/plain', 'isuru')
            shikai.append(izuru)
            trash = S3ContentFolder(name='trash')
            bleach.append(trash)
            documents = S3ContentFolder(name='documents')
            bleach.append(documents)
            documents.append(S3File(b'shinigami', 'text/plain', 'shinigami'))
            documents.append(S3File(b'asauchi', 'text/plain', 'asauchi'))

        # rename file
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            shikai = bleach['chikai']
            izuru = shikai['isuru']
            shikai.rename(izuru, 'izuru')

        # test renamed file
        with mock_dataserver.mock_db_trans(self.ds):
            izuru = self.ds.root['bleach']['chikai']['izuru']
            s3 = IS3FileIO(izuru)
            assert_that(s3.key(), is_('chikai/izuru'))
            assert_that(s3.exists(), is_(True))

        # rename directory
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            bleach.rename('chikai', 'shikai')

        # test renamed directory
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            shikai = bleach['shikai']
            izuru = shikai['izuru']

            s3 = IS3FileIO(shikai)
            assert_that(s3.key(), is_('shikai/'))
            assert_that(s3.exists(), is_(True))

            s3 = IS3FileIO(izuru)
            assert_that(s3.key(), is_('shikai/izuru'))
            assert_that(s3.exists(), is_(True))
            assert_that(s3.contents(), is_('wabisuke'))

        # move file
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            trash = bleach['trash']
            documents = bleach['documents']
            documents.moveTo('shinigami', trash)

        # test moved file
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            shinigami = bleach['trash']['shinigami']
            s3 = IS3FileIO(shinigami)
            assert_that(s3.key(), is_('trash/shinigami'))
            assert_that(s3.exists(), is_(True))
            assert_that(s3.contents(), is_(b'shinigami'))

        s3 = S3FileIO()
        assert_that(s3.exists('documents/shinigami'), is_(False))

        # move directory file
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            trash = bleach['trash']
            bleach.moveTo('documents', trash)

        # test moved directory
        with mock_dataserver.mock_db_trans(self.ds):
            bleach = self.ds.root['bleach']
            documents = bleach['trash']['documents']
            s3 = IS3FileIO(documents)
            assert_that(s3.key(), is_('trash/documents/'))

            asauchi = documents['asauchi']
            s3 = IS3FileIO(asauchi)
            assert_that(s3.exists(), is_(True))
            assert_that(s3.key(), is_('trash/documents/asauchi'))
            assert_that(s3.contents(), is_(b'asauchi'))

        # test clear directory
        with mock_dataserver.mock_db_trans(self.ds):
            trash = self.ds.root['bleach']['trash']
            trash.clear()

        s3 = S3FileIO()
        assert_that(s3.exists('trash/documents/'), is_(True))
        assert_that(s3.exists('trash/documents/asauchi'), is_(False))

        # test delete directory
        with mock_dataserver.mock_db_trans(self.ds):
            del self.ds.root['bleach']['trash']
            del self.ds.root['bleach']['shikai']
            del self.ds.root['bleach']['bankai']

        s3 = S3FileIO()
        assert_that(s3.exists('shikai/'), is_(False))
        assert_that(s3.exists('bankai/'), is_(False))
