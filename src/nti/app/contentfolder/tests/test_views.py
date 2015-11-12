#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestContentFolderViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_operations(self):
        data = {'name': 'CLC3403'}
        res = self.testapp.post_json( '/dataserver2/ofs/root/@@mkdir',
                                      data,
                                      status=201 )
        assert_that(res.json_body, 
                    has_entries('OID', is_not(none()),
                                'NTIID', is_not(none()) ))
        
        res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200 )
        assert_that(res.json_body, 
                    has_entries('ItemCount', is_(1),
                                'Items', has_length(1)))

