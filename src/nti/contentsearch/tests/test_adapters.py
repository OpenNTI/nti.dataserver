#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import close_to
from hamcrest import equal_to
from hamcrest import has_length
from hamcrest import assert_that

import os
import json
import unittest

from nti.chatserver.messageinfo import MessageInfo

from nti.dataserver.users import User
from nti.dataserver.interfaces import INote
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Redaction
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.contenttypes import CanvasTextShape

from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch.discriminators import get_keywords

from nti.contentsearch.interfaces import IACLResolver
from nti.contentsearch.interfaces import ITypeResolver
from nti.contentsearch.interfaces import IContentResolver
from nti.contentsearch.interfaces import INoteContentResolver
from nti.contentsearch.interfaces import IHighlightContentResolver
from nti.contentsearch.interfaces import IRedactionContentResolver
from nti.contentsearch.interfaces import IMessageInfoContentResolver

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import find_test
from nti.contentsearch.tests import SharedConfiguringTestLayer

class AdapterTestLayer(SharedConfiguringTestLayer):

	@classmethod
	def setUp(cls):
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)

		path = os.path.join(os.path.dirname(__file__), 'note2.json')
		with open(path, "r") as f:
			cls.note = json.load(f)

	@classmethod
	def tearDown(cls):
		cls.note = cls.messageinfo = None

	@classmethod
	def testSetUp(cls, test=None):
		test = test or find_test()
		test.note = cls.note
		test.messageinfo = cls.messageinfo

	@classmethod
	def testTearDown(cls):
		pass

class TestContentUtils(unittest.TestCase):

	layer = AdapterTestLayer

	def _create_note(self, msg, username, containerId=None, tags=('ichigo',), canvas=None):
		note = Note()
		note.tags = INote['tags'].fromObject(tags)
		body = [unicode(msg)]
		if canvas:
			body.append(canvas)
		note.body = body
		note.creator = username
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	def _create_user(self, ds=None, username='nt@nti.com', password='temp001'):
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_note_adapter(self):
		usr = self._create_user()
		containerId = make_ntiid(nttype='bleach', specific='manga')
		note = self._create_note('nothing can be explained', usr.username, containerId)
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject(note)
		adapted = INoteContentResolver(note)
		assert_that(adapted.content, is_('nothing can be explained'))
		assert_that(adapted.references, has_length(0))
		assert_that(adapted.ntiid, is_not(None))
		assert_that(adapted.creator, is_('nt@nti.com'))
		assert_that(adapted.containerId, is_(containerId))
		assert_that(adapted.keywords, is_(()))
		assert_that(adapted.tags, is_(['ichigo']))
		assert_that(adapted.sharedWith, has_length(0))
		assert_that(adapted.lastModified, is_not(None))
		assert_that(ITypeResolver(note).type, is_('note'))
		assert_that(IACLResolver(note).acl, is_([usr.username]))

	@WithMockDSTrans
	def test_note_adapter_canvas(self):
		c = Canvas()
		ct = CanvasTextShape()
		ct.text = 'Mike Wyzgowski'
		c.append(ct)
		usr = self._create_user()
		containerId = make_ntiid(nttype='bleach', specific='manga')
		note = self._create_note('New Age', usr.username, containerId, canvas=c)
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject(note)
		adapted = IContentResolver(note)
		assert_that(adapted.content, is_('New Age Mike Wyzgowski'))

	@WithMockDSTrans
	def test_redaction_adpater(self):
		username = 'kuchiki@bleach.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		user = self._create_user(username=username)
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		update_from_external_object(redaction,
					{'replacementContent': u'my redaction',
					 'redactionExplanation': u'Have overcome it everytime I have been on the verge of death'})
		redaction.creator = username
		redaction.containerId = containerId
		redaction = user.addContainedObject(redaction)
		adapted = IRedactionContentResolver(redaction)
		assert_that(adapted.content, is_('Fear'))
		assert_that(adapted.replacementContent, is_('my redaction'))
		assert_that(adapted.redactionExplanation, is_('Have overcome it everytime I have been on the verge of death'))
		assert_that(adapted.references, has_length(0))
		assert_that(adapted.ntiid, is_not(None))
		assert_that(adapted.creator, is_('kuchiki@bleach.com'))
		assert_that(adapted.containerId, is_(containerId))
		assert_that(adapted.keywords, has_length(0))
		assert_that(adapted.sharedWith, has_length(0))
		assert_that(adapted.lastModified, is_not(None))
		assert_that(adapted.type, is_('redaction'))

	@WithMockDSTrans
	def test_highlight_adpater(self):
		username = 'urahara@bleach.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		user = self._create_user(username=username)
		highlight = Highlight()
		highlight.selectedText = u'Kon saw it! The Secret of a Beautiful Office Lady'
		highlight.creator = username
		highlight.containerId = containerId
		highlight = user.addContainedObject(highlight)
		adapted = IHighlightContentResolver(highlight)
		assert_that(adapted.content, is_('Kon saw it! The Secret of a Beautiful Office Lady'))
		assert_that(adapted.references, is_(()))
		assert_that(adapted.ntiid, is_not(None))
		assert_that(adapted.creator, is_('urahara@bleach.com'))
		assert_that(adapted.containerId, is_(containerId))
		assert_that(adapted.keywords, has_length(0))
		assert_that(adapted.sharedWith, has_length(0))
		assert_that(adapted.lastModified, is_not(None))
		assert_that(adapted.type, is_('highlight'))

	@WithMockDSTrans
	def test_messageinfo_adapter_canvas(self):
		c = Canvas()
		ct = CanvasTextShape()
		ct.text = u'Ichigo VS Ulquiorra'
		c.append(ct)
		mi = MessageInfo()
		mi.Body = [u'Beginning of Despair, the Unreachable Blade', c]
		adapted = IMessageInfoContentResolver(mi)
		assert_that(adapted.content, is_('Beginning of Despair, the Unreachable Blade Ichigo VS Ulquiorra'))
		assert_that(adapted.type, is_('messageinfo'))

	def test_dict_adpater(self):
		adapted = IContentResolver(self.note)
		assert_that(adapted.type, is_('note'))
		assert_that(adapted.content, is_('Eddard Stark Lord of Winterfell'))
		assert_that(adapted.references, has_length(0))
		assert_that(adapted.creator, is_('carlos.sanchez@nextthought.com'))
		assert_that(adapted.keywords, has_length(0))
		assert_that(adapted.sharedWith, has_length(0))
		assert_that(adapted.lastModified, is_(close_to(1334000544.120, 0.05)))
		assert_that(adapted.containerId, is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(adapted.ntiid, is_('tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0932:5573657273'))

	@WithMockDSTrans
	def test_canvas_adapter(self):
		marker = object()
		c = Canvas()
		ct = CanvasTextShape()
		ct.text = u'Ichigo'
		c.append(ct)
		adapted = IContentResolver(c)
		assert_that(adapted.content, is_('Ichigo'))
		kws = get_keywords(c, marker)
		assert_that(kws, equal_to(marker))
