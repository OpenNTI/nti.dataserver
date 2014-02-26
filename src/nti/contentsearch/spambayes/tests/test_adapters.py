#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch.spambayes.interfaces import ISpamManager
from nti.contentsearch.spambayes.interfaces import ISpamClassifier

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.spambayes.tests import SharedConfiguringTestLayer

class TestAdapters(unittest.TestCase):
		
	layer = SharedConfiguringTestLayer

	@WithMockDSTrans
	def test_user_classifer(self):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username='nt@nti.com', password='temp001' )
		usp = ISpamClassifier(usr, None)
		usp.train(u'test string', True)
		usp.train(u'another text', True)
		usp.untrain(u'test string', True)
		usp.classify('another text')
		
	@WithMockDSTrans
	def test_user_spam_manager(self):
		usr = User.create_user(username='nt@nti.com', password='temp001' )
		manager = ISpamManager(usr, None)
		
		note = Note()
		msg = u'The final fight of Byakuya and Ichigo'
		note.body = [msg]
		note.creator = 'nt@nti.com'
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note = usr.addContainedObject( note ) 
		
		manager.mark_spam(note)
		assert_that(manager.is_spam(note), is_(True))
		
		manager.unmark_spam(note)
		assert_that(manager.is_spam(note), is_(False))

