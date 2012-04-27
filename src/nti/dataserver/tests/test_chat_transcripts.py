#!/usr/bin/env python

from hamcrest import assert_that, is_

from nti.dataserver import users
from nti.dataserver import chat_transcripts

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
