#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 34 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 34

import math
import collections

from zope import component
from zope.component.hooks import site, setHooks

from zope.generations.utility import findObjectsMatching

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
	c = math.cos(rad)
	s = math.sin(rad)
	return multiply(shapeTransform,  [c,s,-s,c,0,0])

def migrate( obj ):
	polygon_cnt = 0
	scalar = math.cos(math.pi/4.0)
	angle = -math.pi/4.0
	for item in obj.body:
		if isinstance( item, Canvas ):
			for i, shape in enumerate(item.shapeList):
				if not isinstance( shape, _CanvasPolygonShape ) or shape.sides != 4:
					continue

				tx = shape.transform
				st = (tx.a, tx.b, tx.c, tx.d, tx.tx, tx.ty)
				st = scale(st, scalar)
				st = rotate(st, angle)
				tx.a, tx.b, tx.c, tx.d, tx.tx, tx.ty = st
				shape.transform = tx
				item.shapeList[i] = shape
				polygon_cnt += 1

	return polygon_cnt

def needs_migrate(x):
	"""
	Something needs migrated if it has an iterable 'body'. This catches
	Notes, the most common thing, but also the MessageInfo objects stored under
	annotations of users.
	"""
	try:
		return isinstance( x.body, collections.Iterable)
	except (KeyError,AttributeError): # Key error can be a POSKeyError, raised when cross-db things go missing
		return False

def evolve( context ):
	"""
	Evolve generation 32 to generation 33 by scaling and rotating existing squares.
	"""
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			for obj in findObjectsMatching( user, needs_migrate ):
				__traceback_info__ = user, obj
				migrate( obj )
