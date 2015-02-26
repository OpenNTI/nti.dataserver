#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import Mapping

from zope import component

from zc import intid as zc_intid

from ZODB.interfaces import IBroken
from ZODB.POSException import POSError

from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import IDynamicSharingTarget

from nti.externalization.interfaces import LocatedExternalDict

from nti.zodb import readCurrent

def is_broken(obj):
	result = (obj is None)
	if not result:
		try:
			if hasattr(obj, '_p_activate'):
				obj._p_activate()
			result = IBroken.providedBy(obj)
		except POSError:
			result = True
	return result

def _getId(obj, attribute='_ds_intid'):
	try:
		getattr(obj, attribute, None)
	except Exception:
		return None

def remove_broken_objects(user, include_ontainers=True, include_stream=True, 
						  include_shared=True, include_dynamic_friends=False,
						  only_ntiid_containers=True):
		"""
		Returns an iterable across the NTIIDs that are relevant to this user.
		"""
		
		intids = component.queryUtility( zc_intid.IIntIds )
		attribute = intids.attribute
		
		result = LocatedExternalDict()
				
		def _remove(key, obj, container=None):
			if container is not None:
				del container[key]
				result[key] = str(type(obj)) # record
						
			uid = key
			if not isinstance(uid, int):
				uid = _getId(obj, attribute)
				
			if uid is not None:
				intids.forceUnregister(uid, notify=True, removeAttribute=False)
	
		def _loop_and_remove(container, unwrap=True):
			if isinstance(container, Mapping):
				readCurrent(container, False)
				f_unwrap = getattr(container, '_v_unwrap', lambda x:x)
				for key in list(container.keys()):
					value = container[key]
					value = f_unwrap(value) if unwrap else value
					if is_broken(value):
						_remove(key, value, container)
					elif IStreamChangeEvent.providedBy(value) and is_broken(value.object):
						_remove(key, value, container)
				
		if include_ontainers:
			for name, container in user.containers.iteritems():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					result += _loop_and_remove(container, True)

		if include_stream:
			for name, container in user.streamCache.iteritems():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					result += _loop_and_remove(container, False)

		if include_shared:
			
			for name, container in user.containersOfShared.items():
				if not only_ntiid_containers or user._is_container_ntiid(name):
					result += _loop_and_remove(container, False)
								
			if include_dynamic_friends:
				
				dynamic_friends = {	x for x in user.friendsLists.values() 
						  			if IDynamicSharingTarget.providedBy(x) }
	
				interesting_dynamic_things = set(user.dynamic_memberships) | dynamic_friends
				for dynamic in interesting_dynamic_things:
					if include_shared and hasattr( dynamic, 'containersOfShared' ):
						for name, container in dynamic.containersOfShared.items():
							if not only_ntiid_containers or user._is_container_ntiid(name):
								result += _loop_and_remove(container, False)
								
					if include_stream and hasattr( dynamic, 'streamCache' ):
						for name, container in dynamic.streamCache.iteritems():
							if not only_ntiid_containers or user._is_container_ntiid(name):
								result += _loop_and_remove(container, False)
		return result
