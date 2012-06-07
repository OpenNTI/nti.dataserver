#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In some cases, it is necessary to represent resources in something other than the
default configured type. This module defines a way to store and query
overrides for the representation type for any given resource, based on the source text of
the resource. For details, see the factor :func:`ResourceTypeOverrides`.

$Id$
"""
from __future__ import print_function, unicode_literals

import os

logger = __import__( 'logging' ).getLogger( __name__ )
def _lwarn( *args ):
	logger.warn( *args )

def _raise( msg, *args ):
	raise ValueError( msg % args )

def ResourceTypeOverrides( location, fail_silent=True):
	"""
	Given a directory containing a file named ``resourcetypes.txt``, loads and returns
	an object (a dict-like object) to query for overrides.

	That file is an index file in ``name=type1,type2`` format. The ``name`` is a relative path to a file
	giving the source of the resource of which to change the type. The types are the names of representations
	to generate when that source is encountered.

	:param bool fail_silent: If true (the default for backwards compatibility), missing filenames or
		files not found will not raise exceptions.
	"""

	warn = _lwarn if fail_silent else _raise

	if not location:
		warn( "Resource override directory not given" )

	return _load_overrides_from_file( location, warn ) if location else {}

ResourceTypeOverrides.OVERRIDE_INDEX_NAME = 'resourcetypes.txt'

def _load_overrides_from_file(location, warn):
	result = {}

	overridesFile = os.path.join(location, ResourceTypeOverrides.OVERRIDE_INDEX_NAME)

	if not os.path.exists(overridesFile):
		warn('%s not found.  No resourceType overrides will be applied', overridesFile)
		return result


	with open(overridesFile, 'r') as f:
		for line in f.readlines():
			sourceFileName, types = line.split('=')
			types = types.split(',')
			types = [t.strip() for t in types]

			sourcePath = os.path.join(location, sourceFileName)

			if not os.path.exists(sourcePath):
				warn("Can't apply override for %s.  File does not exist", sourcePath)
				continue

			with open(sourcePath, 'r') as sourceFile:
				# TODO: Why this particular algorithm to make the key?
				# Is this something plastex does? Or are these steps duplicated in the code somewhere?
				source = sourceFile.read().strip()
				source = ''.join(source.split())
				result[source] = types


	return result
