#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Remove user indexed content

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from .. import get_indexable_types
from ..common import normalize_type_name as _nrm
from ._repoze_utils import remove_entity_indices

def remove_entity_content(username, content_types=(), include_dfls=False, verbose=False):
	entity = users.Entity.get_entity(username)
	if not entity:
		print("user/entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)
	result = remove_entity_indices(entity, content_types, include_dfls)
	if verbose:
		print("%s catalog(s) removed for user/entity '%s'" % (result, username), file=sys.stderr)

remove_user_content = remove_entity_content

def main():
	arg_parser = argparse.ArgumentParser(description="Unindex user content")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	arg_parser.add_argument('-i', '--include_dfls', help="Unindex content in user's dfls", action='store_true', dest='include_dfls')
	arg_parser.add_argument('-t', '--types',
							 nargs="*",
							 dest='idx_types',
							 help="The content type(s) to unindex")
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	idx_types = args.idx_types
	include_dfls = args.include_dfls
	env_dir = os.path.expanduser(args.env_dir)
	if not idx_types:
		content_types = get_indexable_types()
	else:
		content_types = {_nrm(n) for n in idx_types if _nrm(n) in get_indexable_types()}
		if not content_types:
			print("No valid content type(s) were specified")
			sys.exit(3)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.contentsearch,),
						function=lambda: remove_entity_content(username, content_types, include_dfls, verbose))

if __name__ == '__main__':
	main()
