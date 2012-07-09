#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import os
import sys
import json
import pkg_resources

from zope import interface
from zope.generations import interfaces as gen_interfaces

import nti.dataserver.quizzes as quizzes
import nti.dataserver.classes as classes
import nti.dataserver.providers as providers

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
	minimum_generation = 8

	def __init__( self, *args ):
		pass

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
				   'leo.parker', 'troy.daley', 'steve.johnson' ):
			USERS.append( (uid + '@nextthought.com', uid.replace( '.', ' ').title() ) )

		# Add test users
		max_test_users = 201
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
		aopsCommunity = Community( "Art Of Problem Solving" )
		aopsCommunity.realname = aopsCommunity.username
		aopsCommunity.alias = 'AOPS'

		drgCommunity = Community( "Delaware Resources Group" )
		drgCommunity.realname = drgCommunity.username
		drgCommunity.alias = 'DRG'

		ntiCommunity = Community( 'NextThought' )
		ntiCommunity.realname = ntiCommunity.username
		ntiCommunity.alias = 'NTI'

		mathcountsCommunity = Community( 'MathCounts' )
		mathcountsCommunity.realname = mathcountsCommunity.username
		mathcountsCommunity.alias = 'MathCounts'
		
		testUsersCommunity = Community( 'TestUsers' )
		testUsersCommunity.realname = testUsersCommunity.username
		testUsersCommunity.alias = 'TestUsers'

		return (aopsCommunity, drgCommunity, ntiCommunity, testUsersCommunity)

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

		fl = FriendsList( 'Command and Control' )
		fl.creator = for_user
		fl.addFriend( 'darth.vader@nextthought.com' )
		fl.addFriend( 'jeanluc.picard@nextthought.com' )
		fl.addFriend( 'obiwan.kenobi@nextthought.com' )
		fl.containerId = 'FriendsLists'
		for_user.addContainedObject( fl )

		fl = FriendsList( 'NTI-OK' )
		fl.creator = for_user
		fl.addFriend( 'chris.utz@nextthought.com' )
		fl.addFriend( 'carlos.sanchez@nextthought.com' )
		fl.addFriend( 'grey.allman@nextthought.com' )
		fl.addFriend( 'jeff.muehring@nextthought.com' )
		fl.addFriend( 'ken.parker@nextthought.com' )
		fl.containerId = 'FriendsLists'
		for_user.addContainedObject( fl )


	def install( self, context ):
		conn = context.connection
		root = conn.root()['nti.dataserver']
		ONLY_NEW = '--only-new' in sys.argv
		if ONLY_NEW:
			def add_user( u ):
				if u.username not in root['users']:
					root['users'][u.username] = u
		else:
			def add_user( u ):
				root['users'][u.username] = u



		communities = self._make_communities()
		for c in communities:
			add_user( c )

		# create users	
				
		USERS = self._make_usernames()
		def create_add_user(user_tuple):
			uname = user_tuple[0]
			is_test_user =  uname.startswith('test.user.')
			password = 'temp001' if is_test_user else user_tuple[1].replace( ' ', '.' ).lower()
			user = User( uname, password=password )
			user.realname = user_tuple[1]
			user.alias = user_tuple[1].split()[0]
			for c in communities:
				if	(c.alias == 'TestUsers' and is_test_user) or \
					(c.alias != 'TestUsers' and not is_test_user):
					user.join_community( c )
					user.follow( c )

			self._add_friendslists_to_user( user )
			add_user( user )
		
		map(create_add_user, USERS)
		

		provider = providers.Provider( 'OU' )
		root['providers']['OU'] = provider
		klass = provider.maybeCreateContainedObjectWithType(  'Classes', None )
		klass.containerId = 'Classes'
		klass.ID = 'CS2051'
		klass.Description = 'CS Class'

		section = classes.SectionInfo()
		section.ID = 'CS2051.101'
		klass.add_section( section )
		section.InstructorInfo = classes.InstructorInfo()
		for username, _ in USERS:
			section.enroll( username )
		section.InstructorInfo.Instructors.append( 'jason.madden@nextthought.com' )
		section.Provider = 'OU'
		provider.addContainedObject( klass )


		# Quizzes
		if not ONLY_NEW or 'quizzes' not in root or 'quizzes' not in root['quizzes']:
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
