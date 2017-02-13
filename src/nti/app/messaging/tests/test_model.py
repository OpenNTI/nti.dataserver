# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """
# .. $Id$
# """
# 
# from __future__ import print_function, unicode_literals, absolute_import, division
# __docformat__ = "restructuredtext en"
# logger = __import__('logging').getLogger(__name__)
# 
# from hamcrest import assert_that
# from hamcrest import contains
# from hamcrest import greater_than
# from hamcrest import has_entries
# from hamcrest import not_
# 
# from hamcrest.core.base_matcher import BaseMatcher
# 
# from zope import interface
# 
# from zope.security.interfaces import IPrincipal
# 
# from nti.dataserver import authorization as nauth
# 
# from nti.dataserver.interfaces import IUser
# 
# from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
# 
# from nti.dataserver.tests.test_authorization_acl import permits
# 
# from nti.dataserver.users.users import User
# 
# from nti.externalization.externalization import toExternalObject
# 
# from ..model import Message
# from ..model import PeerToPeerHousingMessage
# from ..model import ReceivedMessage
# from ..model import ReceivedHousingMessage
# 
# from nti.oubound.housing.tests import OUBoundTestCase
# 
# 
# class ProvidesGivenInterface(BaseMatcher):
# 
# 	def __init__(self, day):
# 		self.interface = interface
# 
# 	def _matches(self, item):
# 		return interface.providedBy(item)
# 
# 	def describe_to(self, description):
# 		description.append_text(interface).append_text(' is provided')
# 
# def provides(interface):
# 	return ProvidesGivenInterface(interface)
# 
# class TestExternalization(OUBoundTestCase):
# 
# 	def test_message(self):
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = Message(Date=1484598451, From=from_user, To=[to_user_1, to_user_2], Subject=subject, body='Piano')
# 		external = toExternalObject(message)
# 		assert_that(from_user, provides(IUser))
# 		assert_that(external, has_entries({'Date': greater_than(0),
# 										   'From': 'user001',
# 										   'To': contains('user002', 'user003'),
# 										   'Subject': subject,
# 										   'body': 'Piano',
# 										   'MimeType': 'application/vnd.nextthought.oubound.housing.message'}))
# 
# 	def test_housing_message(self):
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = PeerToPeerHousingMessage(Date=1484598451, From=from_user, To=[to_user_1, to_user_2], Subject=subject, body='Piano')
# 		external = toExternalObject(message)
# 		assert_that(from_user, provides(IUser))
# 		assert_that(external, has_entries({'Date': greater_than(0),
# 										   'From': 'user001',
# 										   'To': contains('user002', 'user003'),
# 										   'Subject': subject,
# 										   'body': 'Piano',
# 										   'MimeType': 'application/vnd.nextthought.oubound.housing.ptphousingmessage'}))
# 
# 	def test_received_message(self):
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = Message(Date=1484598451, From=from_user, To=[to_user_1, to_user_2], Subject=subject, body='Piano')
# 		received = ReceivedMessage(ViewDate=1484598452, Message=message)
# 		external = toExternalObject(received)
# 		assert_that(from_user, provides(IUser))
# 		assert_that(external, has_entries({'ViewDate': 1484598452,
# 										   'Message': has_entries({'Date': greater_than(0),
# 																   'From': 'user001',
# 																   'To': contains('user002', 'user003'),
# 																   'Subject': subject,
# 																   'body': 'Piano',
# 																   'MimeType': 'application/vnd.nextthought.oubound.housing.message'}),
# 										   'MimeType': 'application/vnd.nextthought.oubound.housing.receivedmessage'}))
# 
# 	def test_received_housing_message(self):
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = PeerToPeerHousingMessage(From=from_user, To=[to_user_1, to_user_2], Subject=subject, body='Piano')
# 		received = ReceivedHousingMessage(ViewDate=1484598452, ReplyDate=1484598453, ForwardDate=1484598454, Message=message)
# 		external = toExternalObject(received)
# 		assert_that(external, has_entries({'ViewDate': 1484598452,
# 										   'ReplyDate': 1484598453,
# 										   'ForwardDate': 1484598454,
# 										   'Message': has_entries({'Date': greater_than(0),
# 																   'From': 'user001',
# 																   'To': contains('user002', 'user003'),
# 																   'Subject': subject,
# 																   'body': 'Piano',
# 																   'MimeType': 'application/vnd.nextthought.oubound.housing.ptphousingmessage'}),
# 										   'MimeType': 'application/vnd.nextthought.oubound.housing.receivedhousingmessage'}))
# 
# class TestACLs(OUBoundTestCase):
# 
# 	@WithMockDSTrans
# 	def test_message_acls(self):
# 		username = 'user001'
# 		username2 = 'test001'
# 		username3 = "user003"
# 		adminUser = 'testadmin001@nextthought.com'
# 
# 		User.create_user(username=username)
# 		User.create_user(username=username2)
# 		User.create_user(username=username3)
# 		User.create_user(username=adminUser)
# 
# 		message = PeerToPeerHousingMessage(From=IPrincipal(username), To=[IPrincipal(username2)], Subject='b', body='Piano')
# 		message.creator = username
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(message, permits(username, action))
# 
# 		for action in (nauth.ACT_READ,):
# 			assert_that(message, permits(username2, action))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE):
# 			assert_that(message, not_(permits(username2, action)))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(message, not_(permits(username3, action)))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(message, not_(permits(adminUser, action)))
