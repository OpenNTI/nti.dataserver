#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Applies ZlibStorage to an existing relstorage instance.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import nti.monkey.patch_gevent_on_import
nti.monkey.patch_gevent_on_import.patch()

import nti.monkey.patch_relstorage_umysqldb_on_import
nti.monkey.patch_relstorage_umysqldb_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import logging
import argparse
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

import ZConfig

from relstorage.storage import RelStorage
from relstorage.zodbconvert import schema_xml

from zc.zlibstorage import compress
from zc.zlibstorage import decompress

def main():
	arg_parser = argparse.ArgumentParser(description="Compress an existing RelStorage database")
	arg_parser.add_argument('config_file',
							help="A zodbconvert-style configuration")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	arg_parser.add_argument('--dry-run', 
							help="Don't actually do anything", 
							action='store_true', dest='dry_run')
	arg_parser.add_argument('--limit', 
							help="Only attempt to compress this many rows", 
							dest='limit', type=int)
	arg_parser.add_argument('--uncompress', 
							help="Uncompress instead of compress", 
							dest='uncompress', action='store_true')

	args = arg_parser.parse_args()

	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

	schema = ZConfig.loadSchemaFile(StringIO(schema_xml))
	config, _ = ZConfig.loadConfig(schema, args.config_file)

	destination = config.destination.open()

	logger.info("Storages opened successfully.")

	if not isinstance(destination, RelStorage):  # assume zlibstorage
		destination = destination.base
	adapter = destination._adapter
	conn, cursor = adapter.connmanager.open_for_load()

	if args.uncompress:
		clause = 'LIKE  ".z%%"'
		action = decompress
	else:
		# Get the uncompressed data that we might want to compress
		# zlibstorage doesn't bother if the size is less than 20;
		# for conversion purposes, we won't bother if the size is
		# less than 40 (arbitrary)
		clause = 'NOT LIKE ".z%%" AND state_size > 40'
		action = compress

	query = 'SELECT zoid, tid, state, state_size from object_state where state ' + clause + ' ORDER BY tid DESC'  # The most recent transactions first
	if args.limit:
		query += ' LIMIT ' + str(args.limit)
	totals = 0
	comp_totals = 0
	comp_count = 0
	count = 0
	up_cursor = None
	if args.dry_run:
		logger.info("Dry run mode: not changing the destination.")
	else:
		up_cursor = conn.cursor()

	cursor.execute(query)
	for zoid, tid, data, size in cursor:
		count += 1
		comp_data = action(data)
		totals += size
		comp_totals += len(comp_data)

		if comp_data != data:
			comp_count += 1
			if not args.dry_run:
				up_cursor.execute("UPDATE object_state SET state=%s, state_size=%s WHERE tid=%s and zoid=%s",
								  (comp_data, len(comp_data), tid, zoid))

	if not args.dry_run:
		conn.commit()
	else:
		conn.rollback()

	print("Read ", count, "records and ", 'uncompressed' if args.uncompress else 'compressed', comp_count, "for a ratio of ", comp_totals / totals)

	destination.close()

if __name__ == '__main__':
	main()
