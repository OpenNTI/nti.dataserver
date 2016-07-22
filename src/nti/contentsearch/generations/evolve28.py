#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content search generation 28.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 28

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

def remove_user_index_data(user):
	count = 0
	annotations = IAnnotations(user, {})
	name = "nti.contentsearch._repoze_adpater._RepozeEntityIndexManager"
	mapping = annotations.get(name, None)
	if mapping is not None:
		try:
			for _, catalog in mapping.items():
				for _, index in catalog.items():
					count += 1
					clear = getattr(index, "clear", None)
					if clear is not None and callable(clear):
						clear()  # remove all docs
			mapping.clear()
		except AttributeError:
			pass
		del annotations[name]
	return count

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	count = 0
	with site(ds_folder):
		assert 	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			count += remove_user_index_data(user)
			if IUser.providedBy(user):
				source = user.friendsLists.values()
				for obj in source:
					if IDynamicSharingTargetFriendsList.providedBy(obj):
						count += remove_user_index_data(user)

	logger.info('Evolution done. %s catalog-indexes removed', count)

def evolve(context):
	"""
	Evolve generation 27 to 28 by removing all index data
	"""
	do_evolve(context)
