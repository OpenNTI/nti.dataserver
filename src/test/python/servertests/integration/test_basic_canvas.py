'''
Created on Nov 14, 2011

@author: ltesti
'''

import time

from servertests import DataServerTestCase
from servertests.contenttypes import CanvasAffineTransform
from servertests.contenttypes import Canvas
from servertests.contenttypes import CanvasPolygonShape
from servertests.integration import contains

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_

class TestBasicCanvas(DataServerTestCase):
	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')

	def setUp(self):
		super(TestBasicCanvas, self).setUp()

		# FIXME:  This is duplicated in alot of places.
		self.ds.getRecursiveStreamData('autocreate', credentials=self.owner)
		self.ds.getRecursiveStreamData('autocreate', credentials=self.target)

		self.CONTAINER = 'test.user.container.%s' % time.time()
		self.ds.setCredentials(self.owner)
		
	def test_creating_a_canvas(self):
		
		# create the object to share
		canvasAffineTransform = CanvasAffineTransform(a=0, b=0, c=0, d=0, tx=.25, ty=.25)
		polygonShape = CanvasPolygonShape(sides=4, transform=canvasAffineTransform, container=self.CONTAINER)
		canvas = Canvas(shapeList=[polygonShape], container=self.CONTAINER)
		createdObj = self.ds.createObject(canvas, adapt=True)
		assert_that(createdObj['id'], is_not(None))
		assert_that(createdObj['shapeList'][0]['sides'], is_(4))
		assert_that(createdObj['shapeList'][0]['transform']['a'], is_(0))
		assert_that(createdObj['shapeList'][0]['transform']['b'], is_(0))
		assert_that(createdObj['shapeList'][0]['transform']['c'], is_(0))
		assert_that(createdObj['shapeList'][0]['transform']['d'], is_(0))
		assert_that(createdObj['shapeList'][0]['transform']['tx'], is_(.25))
		assert_that(createdObj['shapeList'][0]['transform']['ty'], is_(.25))
		
		

if __name__ == '__main__':
	import unittest
	unittest.main()