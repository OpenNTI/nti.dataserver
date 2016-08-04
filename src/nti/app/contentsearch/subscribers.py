#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event listeners related to establishing and maintaining the indexmanager.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

try:
	from gevent import sleep
except ImportError:
	from time import sleep

from zope import component

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zc.lockfile import LockFile
from zc.lockfile import LockError

from nti.contentlibrary.boto_s3 import key_last_modified
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IS3ContentPackage
from nti.contentlibrary.interfaces import IFilesystemContentPackage

from nti.contentsearch.interfaces import IIndexManager
from nti.contentsearch.search_utils import register_content

from nti.zodb.common import make_cache_dir

@component.adapter(IFilesystemContentPackage, IObjectCreatedEvent)
def add_filesystem_index(package, event):
	indexmanager = component.queryUtility(IIndexManager)
	if indexmanager is None:  # pragma: no cover
		return
	register_content(package=package, indexmanager=indexmanager)

@component.adapter(IS3ContentPackage, IObjectCreatedEvent)
def add_s3_index(title, event):
	"""
	Adds an index for things that exist in S3, possibly making a local
	cache of them as needed.
	"""
	indexmanager = component.queryUtility(IIndexManager)
	if indexmanager is None:  # pragma: no cover
		return

	# TODO: We really want a utility to manage this cache.
	# It would be created at startup by the application, and given the name of
	# a directory to use. We would then use it to store and retrieve things,
	# persistently, across restarts.
	index_cache_dir = make_cache_dir('whoosh_content_index',
									 env_var='NTI_INDEX_CACHE_DIR')

	indexname = title.get_parent_key().key
	title_index_cache_dir = os.path.join(index_cache_dir, indexname, 'indexdir')
	if not os.path.isdir(title_index_cache_dir):
		os.makedirs(title_index_cache_dir)

	indexdir_keys = title.key.bucket.list(
							delimiter='/',
							prefix=title.make_sibling_key('indexdir').key + '/')

	# TODO: We are caching based on timestamp. Caching based on version_ids
	# might be more reliable

	lock_tries = 0
	while True:
		# Lock the directory to do this in a nearly-atomic way between workers
		try:
			cache_lock = LockFile(os.path.join(title_index_cache_dir, "cache.lock"))
		except LockError:
			lock_tries += 1
			if lock_tries == 30:
				raise
			logger.debug("Waiting for cache lock on %s", title_index_cache_dir)
			sleep(5 * lock_tries)
		else:
			break
	try:
		for indexdir_key in indexdir_keys:
			local_file = os.path.join(title_index_cache_dir,
									  indexdir_key.key.split('/')[-1])
			__traceback_info__ = title, indexdir_key, local_file
			# Smarmy bastards. We get different answers for key.last_modified
			# (and hence key_last_modified) depending on whether we look at it
			# before or after we have downloaded the file.
			# The string comes back in two different forms, which parse differently
			# (due to timezone parsing) So we need to preserve the before value so we
			# can be consistent
			last_modified = key_last_modified(indexdir_key)
			if 	os.path.exists(local_file) and \
				os.stat(local_file)[os.path.stat.ST_MTIME] >= last_modified:
				logger.debug("Local file as new as remote %s", local_file)
				continue

			# Download the file, and set its last modified time to match
			logger.debug("Caching local file from remote %s", local_file)
			indexdir_key.get_contents_to_filename(local_file)
			# get_contents_to_filename tries to do this, but cannot be trusted
			# It may fail, or it will use the 'after download' time, which won't
			# match the 'before download'
			lm = last_modified or key_last_modified(indexdir_key)  # See comments above
			os.utime(local_file, (lm, lm))
	finally:
		cache_lock.close()

	# Touch some other properties to get them cached.
	# Pay this cost at startup rather than at runtime (TODO: Why is this cost so high?)
	getattr(title, 'lastModified', 0)
	if title.installable:
		getattr(title.archive_unit, 'lastModified', 0)
	# Likewise for some files. (TODO: These could be cached on-disk too)
	try:
		# See contentlibrary/externalization.
		# TODO: Standardize and generalize this
		title.read_contents_of_sibling_entry('nti_default_presentation_properties.json')
		# See authorization_acl
		title.read_contents_of_sibling_entry('.nti_acl')
	except title.TRANSIENT_EXCEPTIONS:
		pass

	register_content(indexmanager=indexmanager,
					 indexname=indexname,
					 indexdir=title_index_cache_dir,
					 ntiid=title.ntiid)

@component.adapter(IContentPackage, IObjectModifiedEvent)
def reset_indexes_when_modified(content_package, event):
	# The cheap and effective thing to do is to unregister
	# and re-register. Note that we CANNOT simply
	# broadcast a pair of Removed/Added events as that would
	# have unknown consequences due to other listeners.
	# Its our own problem that we do not have a more efficient way
	# to deal with this.

	reset_indexes_when_removed(content_package, event)

	if IS3ContentPackage.providedBy(content_package):
		add_s3_index(content_package, event)
	elif IFilesystemContentPackage.providedBy(content_package):
		add_filesystem_index(content_package, event)

@component.adapter(IContentPackage, IObjectRemovedEvent)
def reset_indexes_when_removed(content_package, event):
	# XXX What should we do here? We need the index manager objects
	# to expose modification times. And really to best do that we
	# need to move "down" a level into something more tightly integrated,
	# e.g., nti.app.contentsearch...this would let us tighten up the
	# interface for 'add_book'...although ideally we can move that
	# information down into a set of adapters at that level
	indexmanager = component.queryUtility(IIndexManager)
	if indexmanager is None:  # pragma: no cover
		return
	indexmanager.unregister_content(content_package.ntiid)
