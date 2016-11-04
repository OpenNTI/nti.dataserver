#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import only_contains

from nti.dataserver.contenttypes.note import Note
from nti.dataserver.contenttypes.file import ModeledContentFile

from nti.dataserver_core.interfaces import IModeledContentFile

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.schema.testing import validly_provides
from nti.schema.testing import verifiably_provides

from nti.externalization.tests import externalizes

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestFile(DataserverLayerTest):

	def test_content_file(self):
		ext_obj = {
			'MimeType': 'application/vnd.nextthought.modeledcontentfile',
			'value': GIF_DATAURL,
			'filename': r'file.gif',
			'name':'ichigo'
		}

		factory = find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		internal = factory()
		update_from_external_object(internal, ext_obj, require_updater=True)

		assert_that(internal, has_property('data', is_not(none())))
		assert_that(internal, has_property('contentType', 'image/gif'))
		assert_that(internal, has_property('filename', 'file.gif'))
		assert_that(internal, has_property('name', 'ichigo'))

		assert_that(internal, externalizes(all_of(has_key('FileMimeType'),
												  has_key('filename'),
												  has_key('name'))))

	def test_validation_file(self):
		c = ModeledContentFile()
		assert_that(c, validly_provides(IModeledContentFile))
		assert_that(c, verifiably_provides(IModeledContentFile))

	@WithMockDS
	def test_external_body_with_file(self):
		n = Note()
		c = ModeledContentFile()
		c.name = 'foo.gif'

		n.body = [c]
		n.updateLastMod()
		ext = to_external_object(n)
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that(ext, has_entries("Class", "Note",
									 "body", only_contains(has_entries('Class', 'ModeledContentFile',
																	   'name', 'foo.gif'))))
		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object(n, ext, context=ds)
		assert_that(n.body[0], is_(ModeledContentFile))

	def test_content_file_note(self):
		ext_file = {
			'MimeType': 'application/vnd.nextthought.modeledcontentfile',
			'value': GIF_DATAURL,
			'filename': r'file.gif',
			'name':'ichigo'
		}
		ext_obj = {	"Class": "Note",
					"ContainerId": "tag_nti_foo",
					"MimeType": "application/vnd.nextthought.note",
					"body": ['ichigo', ext_file],
					"title": "bleach"}

		factory = find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		internal = factory()
		update_from_external_object(internal, ext_obj)

		assert_that(internal.body[0], is_('ichigo'))
		assert_that(internal.body[1], is_(ModeledContentFile))
		assert_that(internal.body[1], has_property('data', is_not(none())))
