#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from Acquisition.interfaces import IAcquirer

from zope.component.interfaces import ObjectEvent
from zope.component.interfaces import IObjectEvent

from zope.container.interfaces import IContainer

from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import implementer

from zope.schema import BytesLine

from persistent.interfaces import IPersistent

class IObjectWillBeMovedEvent(IObjectEvent):
	"""
	An object will be moved.
	"""
	oldParent = Attribute("The old location parent for the object.")
	oldName = Attribute("The old location name for the object.")
	newParent = Attribute("The new location parent for the object.")
	newName = Attribute("The new location name for the object.")

class IObjectWillBeAddedEvent(IObjectWillBeMovedEvent):
	"""
	An object will be added to a container.
	"""

class IObjectWillBeRemovedEvent(IObjectWillBeMovedEvent):
	"""
	An object will be removed from a container
	"""

class IObjectClonedEvent(IObjectEvent):
	"""
	An object has been cloned (a la Zope 2).

	This is for Zope 2 compatibility, subscribers should really use
	IObjectCopiedEvent or IObjectAddedEvent, depending on their use
	cases.

	event.object is the copied object, already added to its container.
	Note that this event is dispatched to all sublocations.
	"""

@implementer(IObjectWillBeMovedEvent)
class ObjectWillBeMovedEvent(ObjectEvent):
	"""
	An object will be moved.
	"""

	def __init__(self, obj, oldParent, oldName, newParent, newName):
		ObjectEvent.__init__(self, obj)
		self.oldParent = oldParent
		self.oldName = oldName
		self.newParent = newParent
		self.newName = newName

@implementer(IObjectWillBeAddedEvent)
class ObjectWillBeAddedEvent(ObjectWillBeMovedEvent):
	"""
	An object will be added to a container.
	"""

	def __init__(self, obj, newParent=None, newName=None):
		# if newParent is None:
		# 	newParent = object.__parent__
		# if newName is None:
		# 	newName = object.__name__
		ObjectWillBeMovedEvent.__init__(self, obj, None, None, newParent, newName)

@implementer(IObjectWillBeRemovedEvent)
class ObjectWillBeRemovedEvent(ObjectWillBeMovedEvent):
	"""
	An object will be removed from a container.
	"""

	def __init__(self, obj, oldParent=None, oldName=None):
		# if oldParent is None:
		# 	oldParent = object.__parent__
		# if oldName is None:
		# 	oldName = object.__name__
		ObjectWillBeMovedEvent.__init__(self, obj, oldParent, oldName, None, None)

@implementer(IObjectClonedEvent)
class ObjectClonedEvent(ObjectEvent):
	"""
	An object has been cloned into a container.
	"""

class ITraversable(Interface):

	def absolute_url(relative=0):
		"""
		Return the absolute URL of the object.

		This a canonical URL based on the object's physical
		containment path.  It is affected by the virtual host
		configuration, if any, and can be used by external
		agents, such as a browser, to address the object.

		If the relative argument is provided, with a true value, then
		the value of virtual_url_path() is returned.

		Some Products incorrectly use '/'+absolute_url(1) as an
		absolute-path reference.  This breaks in certain virtual
		hosting situations, and should be changed to use
		absolute_url_path() instead.
		"""

	def absolute_url_path():
		"""
		Return the path portion of the absolute URL of the object.

		This includes the leading slash, and can be used as an
		'absolute-path reference' as defined in RFC 2396.
		"""

	def virtual_url_path():
		"""
		Return a URL for the object, relative to the site root.

		If a virtual host is configured, the URL is a path relative to
		the virtual host's root object.  Otherwise, it is the physical
		path.  In either case, the URL does not begin with a slash.
		"""

	def getPhysicalPath():
		"""
		Get the physical path of the object.

		Returns a path (an immutable sequence of strings) that can be used to
		access this object again later, for example in a copy/paste operation.
		getPhysicalRoot() and getPhysicalPath() are designed to operate
		together.
		"""

	def unrestrictedTraverse(path, default=None):
		"""
		Lookup an object by path.

		path -- The path to the object. May be a sequence of strings or a slash
		separated string. If the path begins with an empty path element
		(i.e., an empty string or a slash) then the lookup is performed
		from the application root. Otherwise, the lookup is relative to
		self. Two dots (..) as a path element indicates an upward traversal
		to the acquisition parent.

		default -- If provided, this is the value returned if the path cannot
		be traversed for any reason (i.e., no object exists at that path or
		the object is inaccessible).

		restricted -- If false (default) then no security checking is performed.
		If true, then all of the objects along the path are validated with
		the security machinery. Usually invoked using restrictedTraverse().
		"""

class IObjectManager(ITraversable, IContainer):
	"""
	Generic object manager

	This interface provides core behavior for collections of heterogeneous
	objects."""

	def _setOb(uid, obj):
		pass

	def _delOb(uid):
		pass

	def _getOb(uid, default=None):
		pass

	def _setObject(uid, obj):
		pass

	def _delObject(uid):
		pass

	def hasObject(uid):
		"""
		Indicate whether the folder has an item by ID.
		"""

	def objectIds():
		"""
		List the IDs of the subobjects of the current object.

		If 'spec' is specified, returns only objects whose meta_types match
		'spec'.
		"""

	def objectValues():
		"""
		List the subobjects of the current object.

		If 'spec' is specified, returns only objects whose meta_types match
		'spec'.
		"""

	def objectItems():
		"""
		List (uid, subobject) tuples for subobjects of the current object.

		If 'spec' is specified, returns only objects whose meta_types match
		'spec'.
		"""

	def objectMap():
		"""
		Return a tuple of mappings containing subobject meta-data.
		"""

class IItem(ITraversable):

	__name__ = BytesLine(title=u"Name")

	title = BytesLine(title=u"Title")

	icon = BytesLine(title=u"Icon",
					 description=u"Name of icon, relative to BASEPATH1")

	def getId():
		"""
		Return the id of the object as a string.

		This method should be used in preference to accessing an id
		attribute of an object directly. The getId method is public.
		"""

	def title_or_id():
		"""
		Return the title if it is not blank and the id otherwise.
		"""

	def title_and_id():
		"""
		Return the title if it is not blank and the id otherwise.

		If the title is not blank, then the id is included in parens.
		"""

class IItemWithName(IItem):
	"""
	Item with name.
	"""

class ISimpleItem(IItem, IPersistent, IAcquirer):

	"""Not-so-simple item.
	"""

class IFolder(IObjectManager, IItem):
	pass
