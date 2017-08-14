#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import ends_with
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import has_property
from hamcrest import contains_string
does_not = is_not

from nti.app.contentfile.interfaces import IExternalLinkProvider

from nti.app.contentfile.view_mixins import to_external_download_oid_href

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

GETTING_STARTED = u'Getting Started.pdf'


class TestDecorators(ApplicationLayerTest):

    ext_obj = {
        'MimeType': 'application/vnd.nextthought.contentblobfile',
        'value': GIF_DATAURL,
        'filename': GETTING_STARTED,
        'name': GETTING_STARTED
    }

    global_obj = {
        'MimeType': 'application/vnd.nextthought.contentblobfile',
        'value': GIF_DATAURL,
        'filename': u'file.pdf',
        'name': u'file.pdf'
    }

    def test_content_file(self):
        ext_obj = self.ext_obj
        assert_that(find_factory_for(ext_obj), is_(not_none()))

        internal = find_factory_for(ext_obj)()
        update_from_external_object(internal, ext_obj, require_updater=True)

        assert_that(internal, externalizes(all_of(has_key('FileMimeType'),
                                                  has_key('filename'),
                                                  has_key('name'),
                                                  has_entry('url', none()),
                                                  has_key('CreatedTime'),
                                                  has_key('Last Modified'))))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_external_href(self):

        with mock_dataserver.mock_db_trans(self.ds):
            ext_obj = self.ext_obj
            internal = find_factory_for(ext_obj)()
            update_from_external_object(internal,
                                        ext_obj,
                                        require_updater=True)
            self.ds.root[GETTING_STARTED] = internal
            href = to_external_download_oid_href(internal)
            assert_that(internal,
                        externalizes(all_of(has_key('OID'),
                                            has_entry('url',
                                                      contains_string('/Getting%20Started.pdf')))))

            adapted_href = IExternalLinkProvider(internal).link()
            for link in (href, adapted_href):
                assert_that(link, starts_with('/dataserver2/Objects/'))
                assert_that(link, ends_with('/@@download/Getting%20Started.pdf'))
            
            ext_obj = self.global_obj
            internal = find_factory_for(ext_obj)()
            update_from_external_object(internal,
                                        ext_obj,
                                        require_updater=True)
            self.ds.root['file.pdf'] = internal
            global_href = to_external_download_oid_href(internal)
            external = to_external_object(internal)

        url = external['url']
        assert_that(url, ends_with('/@@view/file.pdf'))
        assert_that(url, does_not(contains_string('download')))
        assert_that(external['download_url'], ends_with('/@@download/file.pdf'))

        res = self.testapp.get(href, status=200)
        assert_that(res, has_property('content_length', is_(61)))
        assert_that(res, has_property('content_type', is_('image/gif')))

        # Test fetching our global obj
        self.testapp.get(global_href, status=200)
