#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import logging
logger = logging.getLogger( __name__ )
import sys


import nti.dataserver as dataserver
from nti.dataserver.users import User, Community, FriendsList
import nti.dataserver.providers as providers
import nti.dataserver.classes as classes

from zope import component
from zope import interface
from zope.generations import interfaces as gen_interfaces
from nti.dataserver import interfaces as nti_interfaces

_DATA_QUIZ_0 = {'Class': 'Quiz',
				'ID': 'mathcounts-2011-0',
				'Items': {
					u'1': {'Answers': [u'$5$', u'$5.0$'],
								 'Class': 'QuizQuestion',
								 'ID': u'1',
								 'OID': '0x0944',
								 'Text': u'\\begin{problem}  1. {\\emph{\\$ \\tab \\tab \\tab }} If a total of twenty million dollars is to be divided evenly among four million people, how much money, in dollars, will each person receive? \\end{problem}'},
				   u'10': {'Answers': [u'$0$'],
						   'Class': 'QuizQuestion',
						   'ID': u'10',
						   'OID': '0x0943',
						   'Text': u'\\begin{problem}  10. \\emph{\\tab \\tab \\small {sq units}}. Trapezoid ABCD and trapezoid EFGH are congruent. What is the difference between the area of triangle ABC and the area of triangle EFJ? \\begin{figure}[htbp]\\begin{center}  \\includegraphics {images/w1-i3.png} \\end{center}\n\n\\end{figure} \\end{problem}'},
				   u'2': {'Answers': [u'$12$'],
						  'Class': 'QuizQuestion',
						  'ID': u'2',
						  'OID': '0x0946',
						  'Text': u'\\begin{problem}  2.\\emph{\\tab \\tab \\small {sq cm}}. Triangle XYZ has side XZ = 6 cm. Segment YA is perpendicular to XZ. If AY is 4 cm, what is the area of triangle XYZ? \\rightpic {w1-i1.png} \\end{problem}'},
				   u'3': {'Answers': [u'$15.37$'],
						  'Class': 'QuizQuestion',
						  'ID': u'3',
						  'OID': '0x0945',
						  'Text': u'\\begin{problem}  \\leftpic {w1-i2.png} 3. {\\emph{\\$ \\tab \\tab \\tab }} Wilhelmina went to the store to buy a few groceries. When she paid for the groceries with a \\$ 20 bill, she correctly received \\$ 4.63 back in change. How much did the groceries cost? \\end{problem}'},
				   u'4': {'Answers': [u'$9$'],
						  'Class': 'QuizQuestion',
						  'ID': u'4',
						  'OID': '0x0948',
						  'Text': u'\\begin{problem}  4. \\emph{\\tab \\small {multiples}} How many multiples of 8 are between 100 and 175? \\end{problem}'},
				   u'5': {'Answers': [u'$\\frac{2}{3}$'],
						  'Class': 'QuizQuestion',
						  'ID': u'5',
						  'OID': '0x0947',
						  'Text': u'\\begin{problem}  5. \\emph{\\tab \\tab \\tab } A three-digit integer is to be randomly created using each of the digits 2, 3 and 6 once. What is the probability that the number created is even? Express your answer as a common fraction. \\end{problem}'},
				   u'6': {'Answers': [u'$10$'],
						  'Class': 'QuizQuestion',
						  'ID': u'6',
						  'OID': '0x094a',
						  'Text': u'\\begin{problem}  6. \\emph{\\tab \\tab \\tab } In the following arithmetic sequence, what is the value of m? -2, 4, m, 16, . . . \\end{problem}'},
				   u'7': {'Answers': [u'$42$'],
						  'Class': 'QuizQuestion',
						  'ID': u'7',
						  'OID': '0x0949',
						  'Text': u'\\begin{problem}  7. \\emph{\\tab \\tab \\tab } A particular fraction is equivalent to $\\frac{2}{3}$. The sum of its numerator and denominator is 105. What is the numerator of the fraction? \\end{problem}'},
				   u'8': {'Answers': [u'$210$'],
						  'Class': 'QuizQuestion',
						  'ID': u'8',
						  'OID': '0x094c',
						  'Text': u'\\begin{problem}  8. \\emph{\\tab \\tab \\tab } What is the least natural number that has four distinct prime factors? \\end{problem}'},
				   u'9': {'Answers': [u'$6$'],
						  'Class': 'QuizQuestion',
						  'ID': u'9',
						  'OID': '0x094b',
						  'Text': u'\\begin{problem}  9. \\emph{\\tab \\tab \\small {areas}}. The perimeter of a particular rectangle is 24 inches. If its length and width are positive integers, how many distinct areas could the rectangle have? \\end{problem}'}},
		 'Last Modified': 1308874590.196118,
		 'OID': '0x068a'}

_DATA_QUIZ_1 = {'Class': 'Quiz',
		 'ID': 'mathcounts-2011-1',
		 'Items': {u'1': {'Answers': [u'$1$'],
						  'Class': 'QuizQuestion',
						  'ID': u'1',
						  'OID': '0x0963',
						  'Text': u'\\begin{problem}  1.\\emph{\\tab \\tab \\small {cartons}}. The bar graph shows the number of cartons of milk sold per day last week at Jones Junior High. What is the positive difference between the mean and median number of cartons of milk sold per day over the five-day period? \\rightpic {w2-i1.png} \\end{problem}'},
				   u'10': {'Answers': [u'$45$'],
						   'Class': 'QuizQuestion',
						   'ID': u'10',
						   'OID': '0x0962',
						   'Text': u'\\begin{problem}  10.\\emph{\\tab \\tab \\small {degrees}}. Two consecutive angles of a regular octagon are bisected. What is the degree measure of each of the acute angles formed by the intersection of the two angle bisectors? \\end{problem}'},
				   u'2': {'Answers': [u'$13$'],
						  'Class': 'QuizQuestion',
						  'ID': u'2',
						  'OID': '0x0965',
						  'Text': u'\\begin{problem}  \\leftpic {w2-i2.png} 2.\\emph{\\tab \\tab \\small {inches}}. An equilateral triangle PBJ that measures 2 inches on each side is cut from a larger equilateral triangle ABC that measures 5 inches on each side. What is the perimeter of trapezoid PJCA? \\end{problem}'},
				   u'3': {'Answers': [u'$10$'],
						  'Class': 'QuizQuestion',
						  'ID': u'3',
						  'OID': '0x0964',
						  'Text': u'\\begin{problem}  \\leftpic {w2-i3.png} 3.\\emph{\\tab \\tab \\small {boys}}. Currently, $\\frac{1}{4}$ of the members of a local club are boys, and there are 80 members. If no one withdraws from the club, what is the minimum number of boys that would need to join to make the club $\\frac{1}{3}$ boys? \\end{problem}'},
				   u'4': {'Answers': [u'$12$'],
						  'Class': 'QuizQuestion',
						  'ID': u'4',
						  'OID': '0x0967',
						  'Text': u'\\begin{problem}  4.\\emph{\\tab \\tab \\small {outfits}}. If William has 3 pairs of pants and 4 shirts, and an outfit consists of 1 pair of pants and 1 shirt, how many distinct outfits can William create? \\end{problem}'},
				   u'5': {'Answers': [u'$6$'],
						  'Class': 'QuizQuestion',
						  'ID': u'5',
						  'OID': '0x0966',
						  'Text': u'\\begin{problem}  5.\\emph{\\tab \\tab \\small {days}}. Jessica reads 30 pages of her book on the first day. The next day, she reads another 36 pages. On the third day, she reads another 42 pages. If she continues to increase the number of pages she reads each day by 6, how many days will it take her to read a book that has 270 pages? \\end{problem}'},
				   u'6': {'Answers': [u'$\\frac{2}{5}$'],
						  'Class': 'QuizQuestion',
						  'ID': u'6',
						  'OID': '0x0969',
						  'Text': u'\\begin{problem}  6.\\emph{\\tab \\tab \\tab }. A basket of fruit contains 4 oranges, 5 apples and 6 bananas. If you choose a piece of fruit at random from the basket, what is the probability that it will be a banana? Express your answer as a common fraction. \\end{problem}'},
				   u'7': {'Answers': [u'$\\frac{21}{32}$'],
						  'Class': 'QuizQuestion',
						  'ID': u'7',
						  'OID': '0x0968',
						  'Text': u'\\begin{problem}  7.\\emph{\\tab \\tab \\tab }. What number is halfway between $\\frac{5}{8}$ and $\\frac{11}{16}$ ? Express your answer as a common fraction. \\end{problem}'},
				   u'8': {'Answers': [u'$9400$'],
						  'Class': 'QuizQuestion',
						  'ID': u'8',
						  'OID': '0x096b',
						  'Text': u'\\begin{problem}  \\leftpic {w2-i4.png} 8.\\emph{\\tab \\tab \\small {pounds}}. Farmer Fred read that his crop needs a fertilizer that is 8\\%  nitrate for optimal yield. He needs to apply 4 pounds of nitrate per acre. If his field has 188 acres, how many pounds of fertilizer will Fred use? \\end{problem}'},
				   u'9': {'Answers': [u'$228$'],
						  'Class': 'QuizQuestion',
						  'ID': u'9',
						  'OID': '0x096a',
						  'Text': u'\\begin{problem}  9.\\emph{\\tab \\tab \\small {sq in}}. Four squares are cut from the corners of a rectangular sheet of cardboard. It is then folded as shown to make a box that is 15 inches long, 8 inches wide and 2 inches tall. What was the area of the original piece of cardboard? \\begin{figure}[htbp]\\begin{center}  \\includegraphics {images/w2-i5.png} \\end{center}\n\n\\end{figure} \\end{problem}'}},
		 'Last Modified': 1308874597.810725,
		 'OID': '0x0922'}

class ExampleDatabaseInitializer(object):
	interface.implements(gen_interfaces.IInstallableSchemaManager)

	generation = 0
	minimum_generation = 0

	def __init__( self, *args ):
		pass

	def _make_usernames(self):
		"""
		:return: An iterable of two-tuples of userid, realname. email will be used
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
		max_test_users = 16
		for x in range(1, max_test_users):
			uid = 'test.user.%s' % x
			USERS.append( (uid + '@nextthought.com', uid.replace( '.', ' ').title() ) )

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

		return (aopsCommunity, drgCommunity, ntiCommunity)

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
		root = conn.root()
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

		USERS = self._make_usernames()
		for user_tuple in USERS:
			uname = user_tuple[0]
			password = 'temp001' if uname.startswith('test.user.') else user_tuple[1].replace( ' ', '.' ).lower()
			user = User( uname, password=password )
			user.realname = user_tuple[1]
			user.alias = user_tuple[1].split()[0]
			for c in communities:
				user.join_community( c )
				user.follow( c )

			self._add_friendslists_to_user( user )
			add_user( user )


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
			root['quizzes']['quizzes'] = dataserver.ModDateTrackingOOBTree()
			q = dataserver.Quiz()
			q.update( _DATA_QUIZ_1 )

			q.id = _DATA_QUIZ_1['ID']
			root['quizzes']['quizzes'][q.id] = q

			q = dataserver.Quiz()
			q.update( _DATA_QUIZ_0 )

			q.id = _DATA_QUIZ_0['ID']
			root['quizzes']['quizzes'][q.id] = q

