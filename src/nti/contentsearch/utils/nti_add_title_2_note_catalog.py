#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reindex user content 

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import argparse

from zope import component
from ZODB.POSException import POSKeyError

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from nti.contentsearch.utils import find_user_dfls
from nti.contentsearch import _repoze_index
from nti.contentsearch.constants import (note_, title_)
from nti.contentsearch import interfaces as search_interfaces

def _update_rim(entity):
	rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
	catalog = rim.get(note_, None)  if rim is not None else None
	if catalog is None:
		return

	if title_ not in catalog:
		_repoze_index._title_field_creator(catalog, title_, search_interfaces.INoteRepozeCatalogFieldCreator)
		print("Title column added to note catalog for '%s'" % entity)

def _update():

	dataserver = component.getUtility(nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout(dataserver).users_folder

	for user in _users.values():
		try:
			_update_rim(user)
			for dfl in find_user_dfls(user):
				_update_rim(dfl)

		except POSKeyError:
			# broken reference for user
			pass

def main():
	arg_parser = argparse.ArgumentParser(description="Reindex entity content")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	args = arg_parser.parse_args()

	env_dir = os.path.expanduser(args.env_dir)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.contentsearch,),
						function=lambda: _update())

if __name__ == '__main__':
	main()
