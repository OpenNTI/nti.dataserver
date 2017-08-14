#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from nti.contentfolder.adapters import Site

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestAdapters(ApplicationLayerTest):

    ext_obj = {
        'MimeType': 'application/vnd.nextthought.contentblobimage',
        'value': GIF_DATAURL,
        'filename': u'image.gif',
        'name': u'image2.gif'
    }

    @WithSharedApplicationMockDS(users=False, testapp=False)
    @fudge.patch('nti.app.contentfile.adapters.site_adapter')
    def test_adapters(self, mock_site):
        mock_site.is_callable().with_args().returns(Site('bleach.org'))
        with mock_dataserver.mock_db_trans(self.ds):
            ext_obj = self.ext_obj
            obj = find_factory_for(ext_obj)()
            update_from_external_object(obj,
                                        ext_obj,
                                        require_updater=True)
            self.ds.root[obj.filename] = obj
            obj.add_association(obj)  # add itself

            assert_that(INameAdapter(obj, None),
                        has_property('name', is_('image2.gif')))

            assert_that(IFilenameAdapter(obj, None),
                        has_property('filename', is_('image.gif')))

            assert_that(IMimeTypeAdapter(obj, None),
                        has_property('mimeType', is_('application/vnd.nextthought.contentblobimage')))

            assert_that(ISiteAdapter(obj, None),
                        has_property('site', is_('bleach.org')))

            assert_that(IAssociationsAdapter(obj, None),
                        has_property('associations', has_length(1)))
