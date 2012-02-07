#!/usr/bin/env python
"""zope.generations installer for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 1

from zope.generations.generations import SchemaManager

class _DataserverSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _DataserverSchemaManager, self ).__init__(generation=1,minimum_generation=1,package_name='nti.dataserver.generations')


def evolve( context ):
	install_main( context )
	install_chat( context )

from BTrees import OOBTree
from nti.dataserver.chat import PersistentMappingMeetingStorage
from nti.dataserver import datastructures
import copy
from nti.dataserver import users
from persistent.list import PersistentList

def install_chat( context ):

	conn = context.connection
	room_name = 'meeting_rooms'
	sess_conn = conn.get_connection( 'Sessions' )
	sess_root = sess_conn.root()

	if room_name not in sess_root:
		sess_root[room_name] = PersistentMappingMeetingStorage( OOBTree.OOBTree )

def install_main( context ):
	conn = context.connection
	root = conn.root()

	for key in ('users', 'vendors', 'library', 'quizzes', 'providers' ):
		root[key] = datastructures.KeyPreservingCaseInsensitiveModDateTrackingBTreeContainer()
		root[key].__name__ = key

	if 'Everyone' not in root['users']:
		# Hmm. In the case that we're running multiple DS instances in the
		# same VM, our constant could wind up with different _p_jar
		# and _p_oid settings. Hence the copy
		root['users']['Everyone'] = copy.deepcopy( users.EVERYONE_PROTO )
	# This is interesting. Must do this to ensure that users
	# that get created at different times and that have weak refs
	# to the right thing. What's a better way?
	users.EVERYONE = root['users']['Everyone']

	# By keeping track of changes in one specific place, and weak-referencing
	# them elsewhere, we can control how much history is kept in one place.
	# This also solves the problem of 'who owns the change?' We do.
	if not root.has_key( 'changes'):
		root['changes'] = PersistentList()
