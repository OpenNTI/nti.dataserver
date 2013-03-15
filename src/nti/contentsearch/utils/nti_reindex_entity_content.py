#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reindex user content 

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import time
import argparse

from ZODB.POSException import POSKeyError

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch

from . import find_all_indexable_pairs
from .. import interfaces as search_interfaces
from .. import _discriminators as discriminators
from ._repoze_utils import remove_entity_catalogs

def reindex_entity_content(entity, include_dfls=False, verbose=False):

	counter = 0
	t = time.time()

	# remove catalogs for main entity
	remove_entity_catalogs(entity)

	# loop through all user indexable objects
	for e, obj in find_all_indexable_pairs(entity, include_dfls=include_dfls):
		try:
			rim = search_interfaces.IRepozeEntityIndexManager(e, None)
			catalog = rim.get_create_catalog(obj) if rim is not None else None
			if catalog is not None:
				docid = discriminators.query_uid(obj)
				if docid is not None:
					catalog.index_doc(docid, obj)
					counter = counter + 1
				elif verbose:
					print("Cannot find int64 id for %r. Object will not be indexed" % obj)
		except POSKeyError:
			# broken reference for object
			pass

	t = time.time() - t
	if verbose:
		print('%s object(s) reindexed for %s in %.2f(s)' % (counter, entity.username, t))

	return counter

def _reindex_process(username, include_dfls=False, verbose=False):
	entity = users.Entity.get_entity(username)
	if not entity:
		print("entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)
	return reindex_entity_content(entity, include_dfls, verbose)

def main():
	arg_parser = argparse.ArgumentParser(description="Reindex entity content")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	arg_parser.add_argument('-i', '--include_dfls', help="Reindex content in user's dfls", action='store_true', dest='include_dfls')
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	include_dfls = args.include_dfls
	env_dir = os.path.expanduser(args.env_dir)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.contentsearch,),
						function=lambda: _reindex_process(username, include_dfls, verbose))

if __name__ == '__main__':
	main()
