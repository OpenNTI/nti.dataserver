#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestAdapters(ApplicationLayerTest):

    ext_obj = {
        'MimeType': 'application/vnd.nextthought.contentfile',
        'value': GIF_DATAURL,
        'filename': r'image.gif',
        'name': 'image2.gif'
    }

    @WithSharedApplicationMockDS(users=False, testapp=False)
    def test_models(self):
        with mock_dataserver.mock_db_trans(self.ds):
            ext_obj = self.ext_obj
            master = None
            refs = list()
            for idx in range(5):
                obj = find_factory_for(ext_obj)()
                update_from_external_object(obj,
                                            ext_obj,
                                            require_updater=True)
                self.ds.root[str(idx)] = obj
                if idx == 0:
                    master = obj
                    assert_that(master.count_associations(), is_(0))
                    assert_that(master.has_associations(), is_(False))
                else:
                    refs.append(obj)
                    master.add_association(obj)
                    assert_that(master.has_associations(), is_(True))
                    assert_that(master.count_associations(), is_(idx))
            
            master.validate_associations()
            assert_that(master.count_associations(), is_(4))
            assert_that(set(master.associations()), has_length(4))
            
            master.remove_association(refs[0])
            assert_that(master.count_associations(), is_(3))
            assert_that(set(master.associations()), has_length(3))
            
            master.clear_associations()
            assert_that(master.count_associations(), is_(0))
            assert_that(master.has_associations(), is_(False))
            assert_that(set(master.associations()), has_length(0))
            