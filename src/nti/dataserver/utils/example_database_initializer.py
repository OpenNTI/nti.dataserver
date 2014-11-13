#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility to initialize an environment

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import simplejson as json

from zc import intid as zc_intid

from zope import interface
from zope import component
from zope.component.hooks import site, getSite

import zope.generations.generations
from zope.generations import interfaces as gen_interfaces

from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users import User, Community, FriendsList

def load_jfile(jfile):
	path = os.path.join(os.path.dirname(__file__), jfile)
	with open(path, "r") as f:
		return json.load(f)

_DATA_QUIZ_0 = load_jfile('example_database_quiz0.json')
_DATA_QUIZ_1 = load_jfile('example_database_quiz1.json')

def exampleDatabaseInitializerSubscriber( event ):
	"""
	Subscriber to the :class:`zope.processlifetime.IDatabaseOpenedEvent`.
	If the example database has previously been installed in this
	database, then we provide the schema manager to continue
	its evolution (since the schema manager is optional).
	"""
	with event.database.transaction() as conn:
		root = conn.root()
		generations = root.get( zope.generations.generations.generations_key )
		if generations is not None and 'nti.dataserver-example' in generations:
			component.provideUtility(
				ExampleDatabaseInitializer(),
				name='nti.dataserver-example' )

@interface.implementer(gen_interfaces.IInstallableSchemaManager)
class ExampleDatabaseInitializer(object):


	generation = 8
	max_test_users = 101
	skip_passwords = False
	minimum_generation = 8
	nti_testers = "NTI_TESTERS"

	def __init__( self, *args, **kwargs ):
		"""
		:param int max_test_users: The number of test users to create.
		"""
		for k in ('max_test_users', 'skip_passwords'):
			if k in kwargs:
				setattr( self, k, kwargs.pop( k ) )

	def _make_usernames(self):
		"""
		:return: An iterable of two-tuples of (userid, realname). email will be used
			as userid
		"""
		USERS = [ ('rusczyk@artofproblemsolving.com', 'Richard Rusczyk'),#Aops
				  ('patrick@artofproblemsolving.com', 'Dave Patrick'),
				  ('ethan.berman@nextthought.com', 'Ethan Berman')]

		# Add the ok people
		for uid in ('aaron.eskam', 'andrew.ligon', 'carlos.sanchez', 'chris.hansen', 
					'chris.utz', 'greg.higgins', 'grey.allman', 'jason.madden', 
					'jeff.muehring', 'jonathan.grimes', 'josh.zuech', 'julie.zhu',
					'kaley.white', 'ken.parker',  'pacifique.mahoro', 'peggy.sabatini', 
					'ray.hatfield', 'sean.jones', 'steve.johnson', 'trina.muehring',
					'troy.daley', 'vitalik.buterin'):
			USERS.append( (uid + '@nextthought.com',
						   uid.replace( '.', ' ').title(),
						   uid + '@nextthought.com') )

		# Add test users
		max_test_users = self.max_test_users
		for x in range(1, max_test_users):
			uid = 'test.user.%s' % x
			name = 'TestUser-%s' % x
			USERS.append( (uid + '@nextthought.com', name) )

		# Some busey people
		USERS.append( ('philip@buseygroup.com', 'Philip Busey Jr') )
		USERS.append( ('phil@buseygroup.com', 'Phil Busey') )
		USERS.append( ('cathy@buseygroup.com', 'Cathy Busey') )
		USERS.append( ('clay@buseygroup.com', 'Clay Stanley') )
		USERS.append( ('brian@buseygroup.com', 'Brian Busey') )

		# Example people. Notice that we give them @nextthought.com
		# emails so we can control the gravatars
		for uid in ('luke.skywalker', 'amelia.earhart', 'charles.lindbergh',
					('darth.vader', 'Lord Vader'), ('jeanluc.picard', 'Captain Picard'),
					('obiwan.kenobi', 'General Kenobi') ):
			uname = uid + '@nextthought.com' if isinstance(uid,basestring) else uid[0] + '@nextthought.com'
			rname = uid.replace( '.', ' ' ).title() if isinstance(uid,basestring) else uid[1]
			USERS.append( (uname, rname) )

		# Demo accounts
		USERS.append( ('jessica.janko@nextthought.com', 'Jessica Janko') )
		USERS.append( ('suzie.stewart@nextthought.com', 'Suzie Stewart') )

		return USERS

	def _make_communities(self, ds):
		# Communities
		aopsCommunity = Community.create_entity( ds, username="ArtOfProblemSolving" )
		aopsCommunity.realname = aopsCommunity.username
		aopsCommunity.alias = 'AOPS'

		ntiCommunity = Community.create_entity( ds, username='NextThought' )
		ntiCommunity.realname = ntiCommunity.username
		ntiCommunity.alias = 'NTI'

		mathcountsCommunity = Community.create_entity( ds, username='MathCounts' )
		mathcountsCommunity.realname = mathcountsCommunity.username
		mathcountsCommunity.alias = 'MathCounts'

		testUsersCommunity = Community.create_entity( ds, username=self.nti_testers)
		testUsersCommunity.realname = testUsersCommunity.username
		testUsersCommunity.alias = self.nti_testers

		return (aopsCommunity, ntiCommunity, mathcountsCommunity, testUsersCommunity)

	def _add_friendslists_to_user( self, for_user ):
		if for_user.username != 'jason.madden@nextthought.com':
			return

		fl = FriendsList( 'Pilots' )
		fl.creator = for_user
		fl.addFriend( 'luke.skywalker@nextthought.com' )
		fl.addFriend( 'amelia.earhart@nextthought.com' )
		fl.addFriend( 'charles.lindbergh@nextthought.com' )
		fl.containerId = 'FriendsLists'
		for_user.addContainedObject( fl )

		fl = FriendsList( 'CommandAndControl' )
		fl.creator = for_user
		fl.addFriend( 'darth.vader@nextthought.com' )
		fl.addFriend( 'jeanluc.picard@nextthought.com' )
		fl.addFriend( 'obiwan.kenobi@nextthought.com' )
		fl.containerId = 'FriendsLists'
		for_user.addContainedObject( fl )

		fl = FriendsList( 'NTI_OK' )
		fl.creator = for_user
		fl.addFriend( 'chris.utz@nextthought.com' )
		fl.addFriend( 'carlos.sanchez@nextthought.com' )
		fl.addFriend( 'grey.allman@nextthought.com' )
		fl.addFriend( 'jeff.muehring@nextthought.com' )
		fl.addFriend( 'ken.parker@nextthought.com' )
		fl.containerId = 'FriendsLists'
		for_user.addContainedObject( fl )

	def _add_test_user_friendlist(self, for_user):
		fl = FriendsList( u'FL-' + self.nti_testers)
		for x in range(1, self.max_test_users):
			uid = 'test.user.%s@nextthought.com' % x
			if uid != for_user.username:
				fl.addFriend( uid )
		for_user.addContainedObject( fl )

	def install( self, context ):

		conn = context.connection
		root = conn.root()['nti.dataserver']
		# If we're in tests, we probably already have a site setup
		if getSite() and getSite().getSiteManager() and getSite().getSiteManager().queryUtility( zc_intid.IIntIds ):
			self._install_in_site( context, conn, root )
		else:
			with site( root ):
				self._install_in_site( context, conn, root )

	def _install_in_site( self, context, conn, root ):
		# ONLY_NEW = '--only-new' in sys.argv
		# if ONLY_NEW:
		# 	def add_user( u ):
		# 		if u.username not in root['users']:
		# 			root['users'][u.username] = u
		# else:
		def register_user( u ):
			# Because we're not in that site, we need to make sure the events
			# go to the right place
			utility = component.getUtility( zc_intid.IIntIds )
			_id = utility.register( u )
			#print( u, _id, utility, id(u) )
			assert utility.getObject( _id ) is u

		def add_user( u ):
			assert u.__parent__ is root['users']
			root['users'][u.username] = u
			register_user( u )

		class mock_dataserver(object):
			pass
		mock_dataserver.root = root
		mock_dataserver.shards = root['shards']
		communities = self._make_communities(mock_dataserver)

		USERS = self._make_usernames()
		def create_add_user(user_tuple):
			#from IPython.core.debugger import Tracer;  Tracer()()
			uname = user_tuple[0]
			is_test_user =  uname.startswith('test.user.')
			password = 'temp001' if is_test_user else user_tuple[1].replace( ' ', '.' ).lower()
			if self.skip_passwords:
				# this can speed up creation a lot, the encrpytion is slow. This matters for test cases.
				password = None

			args = {'username':uname, 'password':password,'dataserver':mock_dataserver}
			ext_value = {}
			ext_value['realname'] = user_tuple[1]
			ext_value['email'] = unicode(uname) if len(user_tuple) < 3 else user_tuple[2]
			ext_value['alias'] = user_tuple[1].split()[0] if not is_test_user else user_tuple[1]
			args['external_value'] = ext_value
			user = User.create_user( **args )
			interface.alsoProvides(user, IRecreatableUser)
			register_user( user )

			for  c in communities:
				if	(c.username == self.nti_testers and is_test_user) or \
					(c.username != self.nti_testers and not is_test_user):
					user.record_dynamic_membership( c )
					user.follow( c )

			if not is_test_user:
				self._add_friendslists_to_user( user )

		map(create_add_user, USERS)

	def evolve( self, context, generation ):
		conn = context.connection
		root = conn.root()
		root = root['nti.dataserver']

		# Add a missing community, if needed
		mathcountsCommunity = Community( 'MathCounts' )
		mathcountsCommunity.realname = mathcountsCommunity.username
		mathcountsCommunity.alias = 'MathCounts'
		if mathcountsCommunity.username not in root['users']:
			logger.info( "Creating MathCounts community" )
			root['users'][mathcountsCommunity.username] = mathcountsCommunity
