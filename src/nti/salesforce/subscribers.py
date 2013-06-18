# -*- coding: utf-8 -*-
"""
Salesforce event subscribers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from nti.assessment import interfaces as as_interfaces

from nti.ntiids.ntiids import find_object_with_ntiid

from .chatter import Chatter

@component.adapter(as_interfaces.IQAssessedQuestion, IObjectCreatedEvent)
def question_assessed(assessed_question, event):
	question = find_object_with_ntiid(assessed_question.questionId)
	content = getattr(question, 'content', None)
	if not content:
		text = []
		for q_part in question.parts:
			text.append(getattr(q_part, 'content', ''))
		content = ''.join(text)

	# TODO: get [access/refresh] token
	username = authenticated_userid(get_current_request())
	chatter = Chatter(username)
	chatter.post_text_news_feed_item(content)
