from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 32

from nti.dataserver.contenttypes import Canvas

def migrate( obj ):
	for item in obj.body:
		if isinstance( item, Canvas ):
			if not hasattr(item, "viewportRatio"):
				item.viewportRatio = 1.0

def evolve( context ):
	pass
