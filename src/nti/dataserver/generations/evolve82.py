#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 82

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 82

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.dataserver.interfaces import IUserDigestEmailMetadata

_SENTKEY = 'nti.app.pushnotifications.digest_email.DigestEmailCollector.last_sent'
_COLLECTEDKEY = 'nti.app.pushnotifications.digest_email.DigestEmailCollector.last_collected'

def _delete_annotation( user ):
	user_annotations = IAnnotations( user )
	sent = user_annotations.get( _SENTKEY, 0 )
	collected =	user_annotations.get( _COLLECTEDKEY, 0 )
	for annotation_key in (_SENTKEY, _COLLECTEDKEY):
		try:
			del user_annotations[annotation_key]
		except KeyError:
			pass
	return collected, sent

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site( ds_folder ):
		users_folder = ds_folder['users']
		logger.info( 'Updating digest meta storage for %s entities', len( users_folder) )
		for user in users_folder.values():
			collected, sent = _delete_annotation( user )
			user_meta = IUserDigestEmailMetadata( user, None )
			if user_meta is not None:
				user_meta.last_sent = sent
				user_meta.last_collected = collected

	logger.info( 'nti.dataserver evolve %s complete.', generation )

def evolve(context):
	"""
	Installs digest email metadata storage for users. Should improve
	commit times when running the digest_email job.
	"""
	do_evolve(context)

