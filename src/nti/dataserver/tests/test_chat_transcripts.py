#!/usr/bin/env python

from hamcrest import assert_that, is_, none, not_none

from nti.dataserver import users
from nti.dataserver import chat_transcripts
from nti.dataserver import interfaces as nti_interfaces

from zope import component
import persistent

def test_add_msg_no_container():
	user = users.User( "sjohnson@nextthought.com" )
	storage = chat_transcripts._UserTranscriptStorageAdapter( user )

	class Meet(object):
		containerId = None
		ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
		id = ID

	class Msg(object):
		containerId = Meet.ID

	assert_that( storage.add_message( Meet, Msg ), is_( False ) )


def test_resolve_transcript_manually( ):

	user = users.User( "sjohnson@nextthought.com" )
	storage = chat_transcripts._UserTranscriptStorageAdapter( user )

	class Meet(persistent.Persistent):
		containerId = 'the_container'
		ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
		id = ID

	class Msg(persistent.Persistent):
		containerId = Meet.ID
		ID = 42
		LastModified = 1
		sharedWith = ()

	assert_that( storage.add_message( Meet(), Msg() ), is_( none() ) )
	# We have no IDataserver, so looking up by OID will fail and we'll have to
	# use manual traversal
	assert_that( component.queryUtility( nti_interfaces.IDataserver ), is_( none() ) )
	assert_that( storage.transcript_for_meeting( Meet.ID ), is_( not_none() ) )
