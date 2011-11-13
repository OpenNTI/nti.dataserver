import time

from servertests import DataServerTestCase
from servertests.contenttypes import CanvasAffineTransform
from servertests.contenttypes import Canvas
from servertests.contenttypes import CanvasPolygonShape
from servertests.integration import contains

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_

class TestBasicNotes(DataServerTestCase):
	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')

	def setUp(self):
		super(TestBasicNotes, self).setUp()

		# FIXME:  This is duplicated in alot of places.
		self.ds.getRecursiveStreamData('autocreate', credentials=self.owner)
		self.ds.getRecursiveStreamData('autocreate', credentials=self.target)

		self.CONTAINER = 'test.user.container.%s' % time.time()
		self.ds.setCredentials(self.owner)

	def test_body_key_is_object(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to post', self.CONTAINER, adapt=True)
		
		#asserts that the shared object contains none.
		assert_that(createdObj['body'][0]), is_("A reply to note")
		assert_that(createdObj['inReplyTo'], is_(None))
		assert_that(createdObj['references'], is_(None))
		assert_that(createdObj['id'], is_not(None))
		
	def test_create_note(self):
		# create the object to share
		createdObj1 =  self.ds.createNote('A note to post', self.CONTAINER, adapt=True)
		
		# asserts that the shared object contains none.
		assert_that(createdObj1, is_not(None))
		
	def test_storing_object_in_body(self):
		
		# create the object to share
		canvasAffineTransform = CanvasAffineTransform(a=0, b=0, c=0, d=0, tx=.25, ty=.25)
		polygonShape = CanvasPolygonShape(sides=4, transform=canvasAffineTransform, container=self.CONTAINER)
		canvas = Canvas(shapeList=[polygonShape], container=self.CONTAINER)
		createdObj = self.ds.createObject(canvas, adapt=True)
		
		createdNote = self.ds.createNote([createdObj], self.CONTAINER, adapt=True)
		assert_that(createdNote['body'][0]['container'], is_(createdObj['container']))
		assert_that(createdObj['id'], is_not(None))
		
	def test_storing_text_and_object_in_body(self):
		
		# create the object to share
		canvasAffineTransform = CanvasAffineTransform(a=0, b=0, c=0, d=0, tx=.25, ty=.25)
		polygonShape = CanvasPolygonShape(sides=4, transform=canvasAffineTransform, container=self.CONTAINER)
		canvas = Canvas(shapeList=[polygonShape], container=self.CONTAINER)
		createdObj = self.ds.createObject(canvas, adapt=True)
		
		createdNote = self.ds.createNote(['check this out' , createdObj], self.CONTAINER, adapt=True)
		assert_that(createdNote['body'][1]['container'], is_(createdObj['container']))
		assert_that(createdObj['id'], is_not(None))

if __name__ == '__main__':
	import unittest
	unittest.main()