#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import os
import json
import pkg_resources

from zc import intid as zc_intid
from zope import interface
from zope.generations import interfaces as gen_interfaces

import nti.dataserver.quizzes as quizzes
import nti.dataserver.classes as classes
import nti.dataserver.providers as providers
from nti.dataserver.users import interfaces as user_interfaces

from nti import deprecated
from nti.dataserver import containers
from nti.dataserver.users import User, Community, FriendsList

import logging
logger = logging.getLogger( __name__ )

def load_jfile(jfile):
	path = os.path.join(os.path.dirname(__file__), jfile)
	with open(path, "r") as f:
		return json.load(f)

_DATA_QUIZ_0 = load_jfile('example_database_quiz0.json')
_DATA_QUIZ_1 = load_jfile('example_database_quiz1.json')

class ExampleDatabaseInitializer(object):
	interface.implements(gen_interfaces.IInstallableSchemaManager)

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
		for uid in ('grey.allman', 'ken.parker', 'logan.testi', 'jason.madden',
				   'chris.utz', 'carlos.sanchez', 'jonathan.grimes',
				   'pacifique.mahoro', 'eric.anderson', 'jeff.muehring',
				   'aaron.eskam',
				   'leo.parker', 'troy.daley', 'steve.johnson','vitalik.buterin' ):
			USERS.append( (uid + '@nextthought.com', uid.replace( '.', ' ').title() ) )

		# Add test users
		max_test_users = self.max_test_users
		for x in range(1, max_test_users):
			uid = 'test.user.%s' % x
			name = 'Test-%s' % x
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

	def _make_communities(self):
		# Communities
		aopsCommunity = Community( "ArtOfProblemSolving" )
		aopsCommunity.realname = aopsCommunity.username
		aopsCommunity.alias = 'AOPS'

		ntiCommunity = Community( 'NextThought' )
		ntiCommunity.realname = ntiCommunity.username
		ntiCommunity.alias = 'NTI'

		mathcountsCommunity = Community( 'MathCounts' )
		mathcountsCommunity.realname = mathcountsCommunity.username
		mathcountsCommunity.alias = 'MathCounts'

		testUsersCommunity = Community( self.nti_testers)
		testUsersCommunity.realname = testUsersCommunity.username
		testUsersCommunity.alias = self.nti_testers

		return (aopsCommunity, ntiCommunity, testUsersCommunity)

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
		# ONLY_NEW = '--only-new' in sys.argv
		# if ONLY_NEW:
		# 	def add_user( u ):
		# 		if u.username not in root['users']:
		# 			root['users'][u.username] = u
		# else:
		def register_user( u ):
			# Because we're not in that site, we need to make sure the events
			# go to the right place
			utility = root.getSiteManager().queryUtility( zc_intid.IIntIds )
			if utility is not None:
				# Support it being missing for the sake of tests (test_evolve17)
				_id = utility.register( u )
				assert utility.getObject( _id ) is u


		def add_user( u ):
			assert u.__parent__ is root['users']
			root['users'][u.username] = u
			register_user( u )

		# TODO: Switch to using Community.create_entity
		communities = self._make_communities()
		for c in communities:
			c.__parent__ = root['users']
			add_user( c )

		# create users
		class mock_dataserver(object):
			pass
		mock_dataserver.root = root
		mock_dataserver.shards = root['shards']
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
			ext_value['email'] = unicode(uname)
			ext_value['realname'] = user_tuple[1]
			ext_value['alias'] = user_tuple[1].split()[0]
			args['external_value'] = ext_value
			user = User.create_user( **args )
			register_user( user )
			for c in communities:
				if	(c.alias == self.nti_testers and is_test_user) or \
					(c.alias != self.nti_testers and not is_test_user):
					user.join_community( c )
					user.follow( c )

			if not is_test_user:
				self._add_friendslists_to_user( user )
			else:
				self._add_test_user_friendlist(user)

		map(create_add_user, USERS)


		provider = providers.Provider( 'OU', parent=root['providers'] )
		root['providers']['OU'] = provider
		klass = provider.maybeCreateContainedObjectWithType(  'Classes', None )
		klass.containerId = 'Classes'
		klass.ID = 'CS2051'
		klass.Description = 'CS Class'
		provider.addContainedObject( klass )

		section = classes.SectionInfo()
		section.ID = 'CS2051.101'
		klass.add_section( section )
		section.InstructorInfo = classes.InstructorInfo()
		for username, _ in USERS:
			section.enroll( username )
		section.InstructorInfo.Instructors.append( 'jason.madden@nextthought.com' )
		section.Provider = 'OU'



		# Quizzes
		if 'quizzes' not in root or 'quizzes' not in root['quizzes']:
			root['quizzes']['quizzes'] = containers.LastModifiedBTreeContainer()
			self._install_quizzes( root )

	def _install_quizzes( self, root ):
		with deprecated.hiding_warnings():
			# Quizzes are pretty much immutable and can be
			# recreated pretty easily
			# Static Quizzes
			q = quizzes.Quiz()
			q.update( _DATA_QUIZ_1 )

			q.id = _DATA_QUIZ_1['ID']
			root['quizzes']['quizzes'][q.id] = q

			q = quizzes.Quiz()
			q.update( _DATA_QUIZ_0 )

			q.id = _DATA_QUIZ_0['ID']
			root['quizzes']['quizzes'][q.id] = q

			# loading quiz from mathcounts2012.json
			with pkg_resources.resource_stream( __name__, 'mathcounts2012.json' ) as data_stream:
				ext_quizzes = json.load(data_stream)
				for data in ext_quizzes:
					q = quizzes.Quiz()
					q.update( data )
					q.id = data['ID']
					root['quizzes']['quizzes'][q.id] = q



	def evolve( self, context, generation ):
		conn = context.connection
		root = conn.root()
		root = root['nti.dataserver']
		self._install_quizzes( root )

		# Add a missing community, if needed
		mathcountsCommunity = Community( 'MathCounts' )
		mathcountsCommunity.realname = mathcountsCommunity.username
		mathcountsCommunity.alias = 'MathCounts'
		if mathcountsCommunity.username not in root['users']:
			logger.info( "Creating MathCounts community" )
			root['users'][mathcountsCommunity.username] = mathcountsCommunity
