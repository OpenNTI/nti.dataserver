#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 33

import math
from collections import Iterable

from zope.generations.utility import findObjectsMatching

from zope import component
from zope.component.hooks import site, setHooks
from nti.dataserver.contenttypes.canvas import Canvas, _CanvasPolygonShape

import logging
logger = logging.getLogger( __name__ )

def multiply(t, m):
	m11 = t[0] * m[0] + t[2] * m[1]
	m12 = t[1] * m[0] + t[3] * m[1]

	m21 = t[0] * m[2] + t[2] * m[3]
	m22 = t[1] * m[2] + t[3] * m[3]

	dx = t[0] * m[4] + t[2] * m[5] + t[4]
	dy = t[1] * m[4] + t[3] * m[5] + t[5]
	
	#(a, b, c, d, tx, ty)
	return (m11, m12, m21, m22, dx, dy)

def scale(shapeTransform, sx, sy=None):
	sy = sx if sy is None else sy
	return multiply(shapeTransform, [sx,0,0,sy,0,0])

def rotate(shapeTransform, rad):
	c = math.cos(rad);
	s = math.sin(rad);
	return multiply(shapeTransform,  [c,s,-s,c,0,0])
	
def migrate( obj ):
	for _, item in enumerate(obj.body):
		if isinstance( item, Canvas ):
			for shape in item.shapeList:
				if not isinstance( shape, _CanvasPolygonShape ) or shape.sides != 4:
					continue
				
				st = (shape._a, shape._b, shape._c, shape._d, shape._tx, shape._ty)
				st = scale(st, math.cos(math.pi/4.0));
				st = rotate(st, -math.pi/4.0)
				shape._a, shape._b, shape._c, shape._d, shape._tx, shape._ty = st
				
def needs_migrate(x):
	"""
	Something needs migrated if it has an iterable 'body'. This catches
	Notes, the most common thing, but also the MessageInfo objects stored under
	annotations of users.
	"""
	return isinstance( getattr( x, 'body', None ), Iterable)

def evolve( context ):
	"""
	Evolve generation 32 to generation 33 by performing a scale and rotation on the transform of existing squares.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			for note in findObjectsMatching( user, needs_migrate):
				__traceback_info__ = user, note
				migrate( note )
