#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

GIF_DATAURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestModel(ApplicationLayerTest):

    ext_obj = {
        'MimeType': 'application/vnd.nextthought.contentblobimage',
        'value': GIF_DATAURL,
        'filename': u'image.gif',
        'name': u'IMGAGE_2.gif'
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
            
    @WithSharedApplicationMockDS(users=False, testapp=False)
    def test_persitance(self):
        with mock_dataserver.mock_db_trans(self.ds):
            obj = find_factory_for(self.ext_obj)()
            update_from_external_object(obj,
                                        self.ext_obj,
                                        require_updater=True)
            assert_that(obj, has_property('name', is_('IMGAGE_2.gif')))
            assert_that(obj, has_property('__name__', is_('image.gif')))
            assert_that(obj.__dict__, does_not(has_key('__name__')))
            self.ds.root['image'] = obj

        with mock_dataserver.mock_db_trans(self.ds):
            image = self.ds.root['image']
            assert_that(image.__dict__, does_not(has_key('__name__')))
            image.__name__ = u'image.gif'
            assert_that(image.__dict__, does_not(has_key('__name__')))
            assert_that(image, has_property('filename', is_('image.gif')))
        
        with mock_dataserver.mock_db_trans(self.ds):
            image = self.ds.root['image']
            assert_that(image, has_property('__name__', is_('image.gif')))
            assert_that(image, has_property('filename', is_('image.gif')))
            assert_that(image.__dict__, does_not(has_key('__name__')))
