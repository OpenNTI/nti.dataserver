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
from .. import get_ugd_indexable_types
from .. import interfaces as search_interfaces
from .. import _discriminators as discriminators
from ..common import normalize_type_name as _nrm
from ..constants import (post_, note_, messageinfo_, highlight_, redaction_)

from . import find_all_posts
from . import find_all_notes
from . import find_all_redactions
from . import find_all_highlights
from . import find_all_messageinfo
from . import find_all_indexable_pairs

_func_map = {
				note_: find_all_notes,
				post_: find_all_posts,
				highlight_: find_all_highlights,
				redaction_: find_all_redactions,
				messageinfo_: find_all_messageinfo
			}

def reindex_entity_content(entity, content_type=None, verbose=False):

	counter = 0
	t = time.time()

	function = _func_map.get(content_type or u'', find_all_indexable_pairs)

	# loop through all user indexable objects
	for e, obj in function(entity):
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

def _reindex_process(username, verbose=False):
	entity = users.Entity.get_entity(username)
	if not entity:
		print("entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)
	return reindex_entity_content(entity, verbose)

def main():
	arg_parser = argparse.ArgumentParser(description="Reindex entity content")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	arg_parser.add_argument('-t', '--type',
							dest='content_type',
							help="The content type to reindex")
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	content_type = args.content_type
	env_dir = os.path.expanduser(args.env_dir)

	if content_type:
		content_type = _nrm(content_type)
		if content_type not in get_ugd_indexable_types():
			print("No valid content type was specified")
			sys.exit(3)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.contentsearch,),
						function=lambda: _reindex_process(username, content_type, verbose))

if __name__ == '__main__':
	main()
