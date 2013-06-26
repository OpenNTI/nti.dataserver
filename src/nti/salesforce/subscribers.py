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

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces

from nti.ntiids.ntiids import find_object_with_ntiid

from .chatter import Chatter
from . import interfaces as sf_interfaces

@component.adapter(as_interfaces.IQAssessedQuestion, IObjectCreatedEvent)
def question_assessed(submission, event):
	question = find_object_with_ntiid(submission.questionId)
	if not question:
		return
	
	username = authenticated_userid(get_current_request())
	user = users.User.get_user(username)
	token = sf_interfaces.ISalesforceTokenInfo(user, None)
	if token is None or not token.can_chatter():
		return

	q_content = getattr(question, 'content', None)
	
	text = []
	count = 1
	for sub_part, q_part in zip(submission.parts, question.parts):
		content = getattr(q_part, 'content', u'')
		value = sub_part.assessedValue
		response = sub_part.submittedResponse
		if not content and q_content and count == 1:
			content = q_content
		text.append("%s) Question: '%s'. Response: '%s', Grade: '%s'" % (count, content, response, value))
		count += 1
		
	profile = user_interfaces.IUserProfile(user)
	realname = getattr(profile, 'realname', None) or username
	
	content = '\n'.join(text)
	content = '%s:\n %s' % (realname, content)
	c = Chatter(user)
	c.post_text_news_feed_item(content)

