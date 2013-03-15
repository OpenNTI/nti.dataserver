#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.contenttypes import Note
from nti.dataserver.activitystream_change import Change

from nti.ntiids.ntiids import make_ntiid

from .._indexagent import _process_event

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (is_, assert_that)

def decorator(f):
	def execute(self, *args, **kwargs):
		self.exception = None
		try:
			f(self, *args, **kwargs)
		except Exception as e:
			self.exception = e
	execute.__name__ = f.__name__
	return execute

class TestIndexAgent(ConfiguringTestBase):

	exception = None
	note_proc = None
	username = 'nt@nti.com'

	def setUp(self):
		super(TestIndexAgent, self).setUp()
		self.exception = None
		self.note_proc = None

	def _create_note(self, msg, containerId=None):
		note = Note()
		note.body = [unicode(msg)]
		note.creator = self.username
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	@WithMockDSTrans
	def test_create(self):
		self.note_proc = self._create_note(u'Kenpachi Zaraki')
		_process_event(self, self.username, Change.CREATED, 'Note', self.note_proc)
		if self.exception:
			self.fail(str(self.exception))

	@WithMockDSTrans
	def test_update(self):
		self.note_proc = self._create_note(u'Aizen')
		_process_event(self, self.username, Change.MODIFIED, 'Note', self.note_proc)
		if self.exception:
			self.fail(str(self.exception))

	@WithMockDSTrans
	def test_delete(self):
		self.note_proc = self._create_note(u'Andy')
		_process_event(self, self.username, Change.DELETED, 'Note', self.note_proc)
		if self.exception:
			self.fail(str(self.exception))

	@decorator
	def _check_call(self, username, type_name, data):
		assert_that('Note', is_(type_name))
		assert_that(self.note_proc, is_(data))
		assert_that(username, is_(self.username))

	# indexmanager

	@decorator
	def index_user_content(self, username, type_name=None, data=None):
		self._check_call(username, type_name, data)

	@decorator
	def update_user_content(self, username, type_name=None, data=None):
		self._check_call(username, type_name, data)

	@decorator
	def delete_user_content(self, username, type_name=None, data=None):
		self._check_call(username, type_name, data)
