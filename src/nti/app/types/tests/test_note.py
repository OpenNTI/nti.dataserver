#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import none
from hamcrest import has_key
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.contentfile.model import ContentBlobFile

from nti.dataserver.tests import mock_dataserver

from nti.externalization.representation import to_json_representation

from nti.ntiids.ntiids import find_object_with_ntiid

GIF_DATAURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestNote(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_create_note(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user()

        ext_file = {
            'MimeType': 'application/vnd.nextthought.contentfile',
            'value': GIF_DATAURL,
            'filename': r'/Users/ichigo/file.gif',
            'name': 'ichigo'
        }
        ext_obj = {"Class": "Note",
                   "ContainerId": "tag_nti_foo",
                   "MimeType": "application/vnd.nextthought.note",
                   "applicableRange": {"Class": "ContentRangeDescription",
                                       "MimeType": "application/vnd.nextthought.contentrange.contentrangedescription"},
                   "body": ['ichigo', ext_file],
                   "tags": ['tag1', 'tag_2'],
                   "title": "bleach"}

        data = to_json_representation(ext_obj)
        # pylint: disable=no-member
        testapp = TestApp(self.app)
        path = '/dataserver2/users/sjohnson@nextthought.com/Objects/'
        res = testapp.post(path, data,
                           extra_environ=self._make_extra_environ(update_request=True),
                           headers={"Content-Type": "application/json"},
                           status=201)
        assert_that(res.json_body,
                    has_entry('body',
                              has_item(has_entries('Class', 'ContentBlobFile',
                                                   'download_url', is_not(none())))))
        assert_that(res.json_body,
                    has_entry('OID', is_not(none())))

        assert_that(res.json_body,
                    has_entry('tags', contains_inanyorder('tag1', 'tag_2')))

        href = res.json_body['href']
        with mock_dataserver.mock_db_trans(self.ds):
            note = find_object_with_ntiid(res.json_body['OID'])
            assert_that(note, is_not(none()))
            assert_that(note,
                        has_property('body',
                                     has_item(is_(ContentBlobFile))))
            assert_that(note.body[1],
                        has_property('__parent__', is_(note)))
            assert_that(note.body[1],
                        has_property('data', is_not(none())))

        durl = res.json_body['body'][1]['download_url']
        res = testapp.get(durl,
                          extra_environ=self._make_extra_environ(),
                          status=200)
        assert_that(res,
                    has_property('body',
                                 has_length(greater_than_or_equal_to(60))))

        res = testapp.get(href + '/@@schema',
                          extra_environ=self._make_extra_environ(),
                          status=200)
        assert_that(res.json_body, has_key('Fields'))
        assert_that(res.json_body, has_key('Constraints'))

    @WithSharedApplicationMockDS
    def test_update_note_direct_data(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user()

        ext_file = {
            'MimeType': 'application/vnd.nextthought.contentfile',
            'value': GIF_DATAURL,
            'filename': r'/Users/ichigo/file.gif',
            'name': 'ichigo'
        }
        ext_obj = {"Class": "Note",
                   "ContainerId": "tag_nti_foo",
                   "MimeType": "application/vnd.nextthought.note",
                   "applicableRange": {"Class": "ContentRangeDescription",
                                       "MimeType": "application/vnd.nextthought.contentrange.contentrangedescription"},
                   "body": ['ichigo', ext_file],
                   "title": "bleach"}

        data = to_json_representation(ext_obj)
        # pylint: disable=no-member
        testapp = TestApp(self.app)
        path = '/dataserver2/users/sjohnson@nextthought.com/Objects/'
        res = testapp.post(path, data,
                           extra_environ=self._make_extra_environ(update_request=True),
                           headers={"Content-Type": "application/json"},
                           status=201)
        path = res.json_body['href']
        durl = res.json_body['body'][1]['download_url']
        # Update
        ext_obj = dict(res.json_body)
        ext_obj['body'][0] = 'Azien'
        data = to_json_representation(ext_obj)
        res = testapp.put(path, data,
                          extra_environ=self._make_extra_environ(),
                          headers={"Content-Type": "application/json"},
                          status=200)

        res = testapp.get(durl,
                          extra_environ=self._make_extra_environ(),
                          status=200)
        assert_that(res,
                    has_property('body',
                                 has_length(greater_than_or_equal_to(60))))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_update_note_multipart(self):
        ext_file = {
            'MimeType': 'application/vnd.nextthought.contentfile',
            'filename': r'/Users/ichigo/ichigo.txt',
            'name': 'ichigo'
        }
        ext_obj = {"Class": "Note",
                   "ContainerId": "tag_nti_foo",
                   "MimeType": "application/vnd.nextthought.note",
                   "applicableRange": {"Class": "ContentRangeDescription",
                                       "MimeType": "application/vnd.nextthought.contentrange.contentrangedescription"},
                   "body": ['ichigo', ext_file],
                   "title": "bleach"}

        path = '/dataserver2/users/sjohnson@nextthought.com/Objects/'

        data = {'__json__': to_json_representation(ext_obj)}
        res = self.testapp.post(path,
                                data,
                                upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
                                status=201)

        durl = res.json_body['body'][1]['download_url']

        res = self.testapp.get(durl, status=200)
        assert_that(res,
                    has_property('body',
                                 has_length(greater_than_or_equal_to(6))))

        # Test validation
        # Current limits: 10 files, 10mb each, 25mb total
        ext_files = []
        upload_files = []
        for idx in range(11):
            new_filename = 'ichigo%s' % idx
            new_ext_file = dict(ext_file)
            new_ext_file['name'] = new_filename
            ext_files.append(new_ext_file)
            upload_files.append((new_filename, 'ichigo.txt', bytes(new_filename)))
        body = ['ichigo']
        body.extend(ext_files)
        ext_obj['body'] = body
        data = {'__json__': to_json_representation(ext_obj)}
        res = self.testapp.post(path,
                                data,
                                upload_files=upload_files,
                                status=422)
        res = res.json_body
        assert_that(res.get('message'),
                    is_('The maximum number of attachments cannot exceed 10.'))
        assert_that(res.get('code'), is_('MaxAttachmentsExceeded'))

        # Total max file size
        body = ['ichigo']
        body.extend(ext_files[:3])
        ext_obj['body'] = body
        data = {'__json__': to_json_representation(ext_obj)}
        new_upload_files = []
        nine_mb_payload = 9485760 * b'x'
        for upload_file in upload_files[:3]:
            new_upload_files.append((upload_file[0], upload_file[1], nine_mb_payload))

        res = self.testapp.post(path,
                                data,
                                upload_files=new_upload_files,
                                status=422)
        res = res.json_body
        assert_that(res.get('message'),
                    is_('The cumulative size of the attached files cannot exceed 25 MB.'))
        assert_that(res.get('code'), is_('MaxTotalAttachmentFileSizeExceeded'))

