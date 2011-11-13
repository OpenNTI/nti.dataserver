import time

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

class TestBasicSharing(DataServerTestCase):

	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')
	unauthorized_target = ('test.user.3@nextthought.com', 'incorrect')
	noteToCreateAndShare = {'text': 'A note to share'}

	def setUp(self):
		super(TestBasicSharing, self).setUp()

		#Changes can't go to users that dont exist so we make sure to autocreate them
		self.ds.getRecursiveStreamData('dontcare', credentials=self.owner)
		self.ds.getRecursiveStreamData('dontcare', credentials=self.target)

		self.CONTAINER = 'TestBasicStream-container-%s' % time.time()
		self.ds.setCredentials(self.owner)
	
	def test_delete_shared_reply(self):
		# create the object to share
		canvasAffineTransform = CanvasAffineTransform(a=0, b=0, c=0, d=0, tx=.25, ty=.25)
		CanvasShape(transform=canvasAffineTransform)
		polygonShape = CanvasPolygonShape(sides=4, container=self.CONTAINER)
		canvas = Canvas(shapeList=[polygonShape], container=self.CONTAINER)
		print canvas
		
		self.ds.createNote(('check this out', canvas), self.CONTAINER, adapt=True)
		
if __name__ == '__main__':
	import unittest
	unittest.main()

