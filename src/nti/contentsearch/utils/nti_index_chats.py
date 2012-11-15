#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from zope import component
from zope.catalog.interfaces import ICatalog

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.users import Entity
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch import interfaces as search_interfaces

def _index_meeting(user, roomid, verbose=False):
	count = 0
	users = set()
	messages = []
	
	storage = chat_interfaces.IUserTranscriptStorage(user, None)
	rim = search_interfaces.IRepozeEntityIndexManager(user, None)
	transcript = storage.transcript_for_meeting(roomid) if storage is not None else None
	if transcript is not None and rim is not None:
		for m in transcript.Messages:
			messages.append(m)
			if rim is not None:
				rim.index_content(m)
				count += 1 
			users.add(m.Creator)
			
	if user.username in users:
		users.remove(user.username)
	
	for username in users:
		e = Entity.get_entity(username)
		rim = search_interfaces.IRepozeEntityIndexManager(e, None) if e is not None else None
		if rim is not None:
			for m in messages:
				rim.index_content(m)
				count += 1 
			
	if verbose:
		print('\t%s records were indexed' % count)
		
	return users

def _index_meetings(created, verbose=False):
	chat_catalog = component.getUtility(ICatalog, name=chat_interfaces.MEETING_CATALOG_NAME)
	meetings = list(chat_catalog.searchResults(created=(created, created)))
	
	if verbose:
		print('Indexing %s meeting(s)' % len(meetings))
		
	for m in meetings:
		if verbose:
			print('\tIndexing meeting %s' % m.RoomId)
			
		user = Entity.get_entity(m.creator)
		if user is not None:
			_index_meeting(user, m.RoomId, verbose)
			
def main():
	arg_parser = argparse.ArgumentParser( description="Return the users that have the opt_in_email_communication set" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'created', help="Meeting creation date in ISO format (e.g. 2012-11-15)" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	verbose = args.verbose
	created = args.created
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: _index_meetings(created, verbose) )
	sys.exit( 0 )
	
if __name__ == '__main__':
	main()
	