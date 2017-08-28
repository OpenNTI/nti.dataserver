#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import ends_with
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import has_property

from nti.property import dataurl

from nti.dataserver.users import interfaces as user_interfaces

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

GIF_DATAURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='
PNG_DATAURL = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACXBIWXMAAAsTAAALEwEAmpwYAAACbmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS4xLjIiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iPgogICAgICAgICA8eG1wOkNyZWF0b3JUb29sPkFjb3JuIHZlcnNpb24gMi42LjU8L3htcDpDcmVhdG9yVG9vbD4KICAgICAgPC9yZGY6RGVzY3JpcHRpb24+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIj4KICAgICAgICAgPHRpZmY6Q29tcHJlc3Npb24+NTwvdGlmZjpDb21wcmVzc2lvbj4KICAgICAgICAgPHRpZmY6WVJlc29sdXRpb24+NzI8L3RpZmY6WVJlc29sdXRpb24+CiAgICAgICAgIDx0aWZmOlhSZXNvbHV0aW9uPjcyPC90aWZmOlhSZXNvbHV0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KO/MupgAAAA1JREFUCB1j+P//PwMACPwC/uYM/6sAAAAASUVORK5CYII='


class TestApplicationZopeFileViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_image_to_dataurl_bad_data(self):
        path = '/dataserver2/@@image_to_dataurl'
        testapp = self.testapp
        testapp.post(path,
                     upload_files=[('field', 'foo.gif', b'bad gif data')],
                     status=400)

    def _do_test_echo(self, url):
        testapp = self.testapp

        path = '/dataserver2/@@image_to_dataurl'
        data, _mimetype = dataurl.decode(url)

        res = testapp.post(path,
                           upload_files=[('field', 'foo.jpeg', data)])
        assert_that(res.status_int, is_(200))
        assert_that(res.body, is_(url))

        res = testapp.post(path,
                           upload_files=[('field', 'foo.jpeg', data)],
                           headers={'Accept': 'application/json'})
        assert_that(res.status_int, is_(200))

        path = path + '_extjs'
        ext_res = testapp.post(path,
                               upload_files=[('field', 'foo.jpeg', data)])
        assert_that(res.status_int, is_(200))

        return res, ext_res

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_image_to_dataurl_GIF(self):
        self._do_test_echo(GIF_DATAURL)

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_image_to_dataurl_PNG(self):
        res, ext_res = self._do_test_echo(PNG_DATAURL)
        assert_that(res.json_body, is_({'dataurl': PNG_DATAURL,
                                        'width_px': 1,
                                        'height_px': 1,
                                        'filename': 'foo.jpeg',
                                        'file_size': 725}))
        assert_that(ext_res.json_body, is_({'dataurl': PNG_DATAURL,
                                            'width_px': 1,
                                            'height_px': 1,
                                            'file_size': 725,
                                            'filename': 'foo.jpeg',
                                            'success': True}))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=False,
                                 user_hook=lambda u: setattr(user_interfaces.IUserProfile(u),
                                                             'avatarURL',
                                                             PNG_DATAURL))
    def test_avatar_view_profile_data(self):
        # Note that we turn default authentication off, because this URL is available
        # to everyone
        ext_user = self.resolve_user(extra_environ=self._make_extra_environ())

        avatar_url = ext_user['avatarURL']
        assert_that(avatar_url, starts_with('/dataserver'))
        assert_that(avatar_url, ends_with('@@avatar_view'))

        res = self.testapp.get(avatar_url)

        assert_that(res, has_property('content_length', 725))
        assert_that(res, has_property('content_type', 'image/png'))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=False,
                                 user_hook=lambda u: setattr(user_interfaces.IUserProfile(u),
                                                             'backgroundURL',
                                                             PNG_DATAURL))
    def test_background_view_profile_data(self):
        # Note that we turn default authentication off, because this URL is available
        # to everyone
        ext_user = self.resolve_user(extra_environ=self._make_extra_environ())

        avatar_url = ext_user['backgroundURL']
        assert_that(avatar_url, starts_with('/dataserver'))
        assert_that(avatar_url, ends_with('@@background_view'))

        res = self.testapp.get(avatar_url)

        assert_that(res, has_property('content_length', 725))
        assert_that(res, has_property('content_type', 'image/png'))
