import time
import random
import threading

from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

from servertests import DataServerTestCase
from servertests.integration import contained_in
from servertests.integration import shared_with
from servertests.integration import has_same_oid_as
from servertests.integration import contains
from servertests import integration
import urllib2
from hamcrest import (assert_that, has_entry, is_, is_not,
					  not_none, greater_than_or_equal_to, has_length)
from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_
from servertests.integration import sortchanges
from servertests.integration import objectsFromContainer
from servertests.integration import wraps_item
import time
import warnings

from servertests import DataServerTestCase
from servertests.integration import container
from servertests.integration import sortchanges
from servertests.integration import of_change_type_circled
from servertests.integration import of_change_type_shared
from servertests.integration import of_change_type_modified
from servertests.integration import objectsFromContainer
from servertests.integration import wraps_item
from servertests.integration import unwrapObject
from servertests.integration import notification_count
from servertests.integration import get_notification_count
import os
import sys
import glob
import time
import socket
import anyjson
import urllib2
import subprocess

from servertests.contenttypes import Note
from servertests.contenttypes import Canvas
from servertests.contenttypes import Sharable
from servertests.contenttypes import Highlight
from servertests.contenttypes import adaptDSObject
from servertests.contenttypes import CanvasPolygonShape
from servertests.contenttypes import CanvasAffineTransform
from servertests.contenttypes import CanvasShape
from servertests.server import DataserverClient
from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

class TestSimpleChat(BasicChatTest):
	
	def setUp(self):
		super(TestSimpleChat, self).setUp()
		self.user_one = self.user_names[0]
		self.user_two = self.user_names[1]
		self.user_three = self.generate_user_name()
		self.register_friends(self.user_three, [self.user_one, self.user_two])
		self.user_four = self.generate_user_name()
		self.register_friends(self.user_four, str((self.user_one, self.user_two)))
		self.user_five = self.generate_user_name()
	
	def test_chadtf(self):
		entries = random.randint(5, 10)
		one, two = run_chat(entries, self.user_three, self.user_four)
		self.assert_(str(one.exception) == 'Could not enter room', "User %s caught exception %s" % (one.username, one.exception))
		self.assert_(str(('%s' % two.exception)[3:15]) == 'Invalid auth', "User %s caught exception %s" % (two.username, two.exception))
		
	def _compare(self, sender, receiver):
		
		_sent = list(sender.sent)
		self.assertTrue(len(_sent) > 0, "%s did not send any messages" % sender)
		_sent.sort()
		
		_recv = list(receiver.received)
		self.assertTrue(len(_recv) > 0, "%s did not get any messages" % receiver)
		_recv.sort()
		
		self.assertEqual(_sent, _recv, "%s did not get all messages from %s" % (receiver, sender))
		
# ----------------------------

def run_chat(entries, user_one, user_two):
	
	connect_event = threading.Event()
	one = User(username=user_one)
	two = User(username=user_two)
		
	print "entries", entries
	
	def two_runnable():
		t_args={'occupants':(user_one), 'entries':entries}
		try:
			time.sleep(1)
			two.ws_connect()
			connect_event.set()
			two(**t_args)
		except Exception, e:
			two.exception = e
			two.ws_capture_and_close()
	
	o_args={'entries':entries, 'connect_event':connect_event}
	o_t=threading.Thread(target=one, kwargs=o_args)
	o_t.start()

	t_t=threading.Thread(target=two_runnable)
	t_t.start()

	for t in (o_t, t_t):
		t.join()
		
	return one, two
			
# ----------------------------

class User(OneRoomUser):
		
	def __call__(self, *args, **kwargs):
		t = time.time()
		try:
			entries = kwargs.get('entries', None)
			occupants = kwargs.get('occupants', None)
					
			# connect
			if not self.ws_connected:
				self.ws_connect()
	
			# check for an connect event
			event = kwargs.get('connect_event', None)
			if event: 
				event.wait(60)
					
			if occupants:
				self.enterRoom(occupants)
				
			self.wait_4_room()
				
			# write any messages
			room_id = self.room
			if room_id:
				self.post_random_messages(room_id, entries, 5)
					
			# get any message
			self.wait_heart_beats()
					
		except Exception, e:
			self.exception = e
		finally:
			self.ws_capture_and_close()
			print "exit %s,%s" % (self, time.time() - t)
	
if __name__ == '__main__':
	import unittest
	unittest.main()

