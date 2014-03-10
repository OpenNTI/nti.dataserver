# -*- coding: utf-8 -*-
"""
Content search generation 28.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 28

from zope import component
from zope.component.hooks import site, setHooks
from zope.annotation import interfaces as an_interfaces

from nti.dataserver import interfaces as nti_interfaces

def remove_user_index_data(user):
	annotations = an_interfaces.IAnnotations(user, {})
	name = "nti.contentsearch._repoze_adpater._RepozeEntityIndexManager"
	mapping = annotations.get(name, None)
	if mapping is not None:
		for cat_name, catalog in mapping.items():
			for key, index in catalog.items():
				m = getattr(index, "clear", None)
				if m is not None and callable(m):
					m()  # remove all docs
					logger.info("Index %s/%s was cleared for user %s", cat_name, key, user)
		mapping.clear()
		del annotations[name]

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert 	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			remove_user_index_data(user)
			if nti_interfaces.IUser.providedBy(user):
				source = user.friendsLists.values()
				for obj in source:
					if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
						remove_user_index_data(user)

	logger.info('Evolution done!!!')

def evolve(context):
	"""
	Evolve generation 27 to 28 by removing all index data
	"""
	do_evolve(context)
