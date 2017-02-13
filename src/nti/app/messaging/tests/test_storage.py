# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# 
# from __future__ import print_function, unicode_literals, absolute_import, division
# __docformat__ = "restructuredtext en"
# 
# # disable: accessing protected members, too many methods
# # pylint: disable=W0212,R0904
# 
# from fudge import Fake
# 
# from hamcrest import is_
# from hamcrest import has_length
# from hamcrest import assert_that
# from hamcrest import same_instance
# from hamcrest import calling
# from hamcrest import raises
# from hamcrest import not_none
# from hamcrest import equal_to
# from hamcrest import is_not
# from hamcrest import not_
# 
# from zope import interface
# 
# from zope.container.interfaces import InvalidItemType
# 
# from nti.dataserver.interfaces import IPrincipal
# from nti.dataserver.interfaces import IUser
# 
# from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
# 
# from nti.dataserver.tests.test_authorization_acl import permits
# from nti.dataserver.tests.test_authorization_acl import denies
# 
# from nti.dataserver.users.users import User
# 
# import nti.dataserver.tests.mock_dataserver as mock_dataserver
# 
# from nti.oubound.housing.messaging.storage import HousingMailbox
# 
# from nti.oubound.housing.tests import OUBoundTestCase
# 
# from nti.dataserver import authorization as nauth
# 
# from ..model import Message
# from ..model import PeerToPeerHousingMessage
# from ..model import ReceivedMessage
# from ..model import ReceivedHousingMessage
# from ..storage import MessageContainer
# from ..storage import HousingMessageContainer
# from ..storage import ReceivedMessageContainer
# from ..storage import ReceivedHousingMessageContainer
# 
# class TestStorage(OUBoundTestCase):
# 
# 	@WithMockDSTrans
# 	def test_message_container(self):
# 		folder = MessageContainer()
# 		mock_dataserver.current_transaction.add(folder)
# 
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		assert_that(message.__parent__, same_instance(None))
# 		assert_that(message.__name__, same_instance(None))
# 
# 		result = folder.appendMessage(message)
# 
# 		assert_that(result, same_instance(message))
# 		assert_that(result.__parent__, same_instance(folder))
# 		assert_that(message.__name__, not_none())
# 
# 		message2 = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		folder.appendMessage(message2)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(2))
# 
# 		folder.deleteMessage(message)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(1))
# 		assert_that(message.__name__ in folder, is_(False))
# 		assert_that(message2.__name__ in folder, is_(True))
# 		assert_that(message.__name__, is_not(equal_to(message2.__name__)))
# 
# 		message3 = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message3.__name__ = message2.__name__
# 		assert_that(calling(folder.appendMessage).with_args(message3), raises(KeyError))
# 
# 		fake_msg = Fake('Message').has_attr(__name__='fakeKey')
# 		assert_that(calling(folder.appendMessage).with_args(fake_msg), raises(InvalidItemType))
# 
# 	@WithMockDSTrans
# 	def test_housing_message_container(self):
# 		folder = HousingMessageContainer()
# 		mock_dataserver.current_transaction.add(folder)
# 
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = PeerToPeerHousingMessage(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		assert_that(message.__parent__, same_instance(None))
# 
# 		result = folder.appendMessage(message)
# 
# 		assert_that(result, same_instance(message))
# 		assert_that(result.__parent__, same_instance(folder))
# 
# 		message2 = PeerToPeerHousingMessage(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		folder.appendMessage(message2)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(2))
# 
# 		folder.deleteMessage(message)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(1))
# 		assert_that(message.__name__ in folder, is_(False))
# 		assert_that(message2.__name__ in folder, is_(True))
# 
# 		message3 = PeerToPeerHousingMessage(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message3.__name__ = message2.__name__
# 		assert_that(calling(folder.appendMessage).with_args(message3), raises(KeyError))
# 
# 		base_message = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		assert_that(calling(folder.appendMessage).with_args(base_message), raises(InvalidItemType))
# 
# 	@WithMockDSTrans
# 	def test_received_message_container(self):
# 		folder = ReceivedMessageContainer()
# 		mock_dataserver.current_transaction.add(folder)
# 
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message.__name__ = '1'
# 		received_message = ReceivedMessage(Message=message)
# 		assert_that(received_message.__parent__, same_instance(None))
# 
# 		result = folder.appendMessage(received_message)
# 
# 		assert_that(result, same_instance(received_message))
# 		assert_that(result.__parent__, same_instance(folder))
# 
# 		message2 = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message2.__name__ = '2'
# 		received_message2 = ReceivedMessage(ViewedDate=1484598451, ReplyDate=1484598452, ForwardDate=1484598453, Message=message2)
# 		folder.appendMessage(received_message2)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(2))
# 
# 		folder.deleteMessage(received_message)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(1))
# 		assert_that(received_message.__name__ in folder, is_(False))
# 		assert_that(received_message2.__name__ in folder, is_(True))
# 
# 		received_message3 = ReceivedMessage(ViewedDate=1484598451, ReplyDate=1484598452, ForwardDate=1484598453, Message=message2)
# 		received_message3.__name__ = received_message2.__name__
# 		assert_that(calling(folder.appendMessage).with_args(received_message3), raises(KeyError))
# 
# 		fake_msg = Fake('Message').has_attr(__name__='fakeKey')
# 		assert_that(calling(folder.appendMessage).with_args(fake_msg), raises(InvalidItemType))
# 
# 	@WithMockDSTrans
# 	def test_received_housing_message_container(self):
# 		folder = ReceivedHousingMessageContainer()
# 		mock_dataserver.current_transaction.add(folder)
# 
# 		from_user = IPrincipal('user001')
# 		to_user_1 = IPrincipal('user002')
# 		to_user_2 = IPrincipal('user003')
# 		subject = 'No strings attached'
# 
# 		message = PeerToPeerHousingMessage(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message.__name__ = '1'
# 		received_message = ReceivedHousingMessage(Message=message)
# 		assert_that(received_message.__parent__, same_instance(None))
# 
# 		result = folder.appendMessage(received_message)
# 
# 		assert_that(result, same_instance(received_message))
# 		assert_that(result.__parent__, same_instance(folder))
# 
# 		message2 = PeerToPeerHousingMessage(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		message2.__name__ = '2'
# 		received_message2 = ReceivedHousingMessage(ViewedDate=1484598451, ReplyDate=1484598452, ForwardDate=1484598453, Message=message2)
# 		folder.appendMessage(received_message2)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(2))
# 
# 		folder.deleteMessage(received_message)
# 
# 		items = [x for x in folder.values()]
# 		assert_that(items, has_length(1))
# 		assert_that(received_message.__name__ in folder, is_(False))
# 		assert_that(received_message2.__name__ in folder, is_(True))
# 
# 		received_message3 = ReceivedHousingMessage(ViewedDate=1484598451, ReplyDate=1484598452, ForwardDate=1484598453, Message=message2)
# 		received_message3.__name__ = received_message2.__name__
# 		assert_that(calling(folder.appendMessage).with_args(received_message3), raises(KeyError))
# 
# 		base_message = Message(Date=1484598451,
# 						  From=from_user,
# 						  To=[to_user_1, to_user_2],
# 						  Subject=subject,
# 						  body='Piano')
# 		base_message.__name__ = '3'
# 		base_received_message = ReceivedMessage(ViewedDate=1484598451, ReplyDate=1484598452, ForwardDate=1484598453, Message=base_message)
# 		assert_that(calling(folder.appendMessage).with_args(base_received_message), raises(InvalidItemType))
# 
# @interface.implementer(IUser)
# class MockUser(object):
# 	username = None
# 
# 	def __init__(self, username):
# 		self.username = username
# 
# class HousingMailboxTest(OUBoundTestCase):
# 
# 	def test_housing_mailbox_creation(self):
# 		mailbox = HousingMailbox(MockUser('jwatson'))
# 
# 		assert_that(mailbox.creator, equal_to('jwatson'))
# 
# class TestACLs(OUBoundTestCase):
# 
# 	@WithMockDSTrans
# 	def test_mailbox_acls(self):
# 		username = 'user001'
# 		username2 = 'test001'
# 
# 		User.create_user(username=username)
# 		User.create_user(username=username2)
# 
# 		mailbox = HousingMailbox(username)
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(mailbox, permits(username, action))
# 
# 		for action in (nauth.ACT_DELETE,):
# 			assert_that(mailbox, not_(permits(username, action)))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(mailbox, not_(permits(username2, action)))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(mailbox, denies(username2, action))
# 
# 		for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE, nauth.ACT_READ):
# 			assert_that(mailbox, permits(nauth.ROLE_ADMIN.id, action))
