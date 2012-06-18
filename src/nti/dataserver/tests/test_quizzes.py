#!/usr/bin/env python2.7

import warnings
from hamcrest import assert_that, has_entry, is_, has_length

import nti.dataserver.quizzes as q

def test_quiz_update_deprecated():
	# We should get two deprecated warnings
	warn_count = []
	def showwarnings( *args ):
		warn_count.append( args )
	orig = warnings.showwarning
	warnings.showwarning = showwarnings

	quiz1 = q.Quiz()
	quiz1.questions['a'] = 1

	quiz2 = q.Quiz()
	quiz2.update( quiz1 )

	assert_that( quiz2.questions, has_entry( 'a', 1 ) )

	quiz2.update( {'Items': {}} )
	assert_that( quiz2.questions, is_( {} ) )

	assert_that( warn_count, has_length( 2 ) )
	warnings.showwarning = orig
