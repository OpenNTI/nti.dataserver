#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_


from zope import component
from zc.displayname.interfaces import IDisplayNameGenerator
from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestDisplayNameGenerators(ApplicationLayerTest):

	def test_note(self):
		from nti.dataserver.contenttypes import Note
		note = Note()
		note.title = IPlainTextContentFragment('the title')
		assert_that( component.getMultiAdapter((note, self.request), IDisplayNameGenerator)(),
					 is_(note.title) )
