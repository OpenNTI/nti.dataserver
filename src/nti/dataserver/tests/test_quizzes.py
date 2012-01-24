#!/usr/bin/env python2.7

import warnings
from hamcrest import assert_that, has_entry, is_

import nti.dataserver.quizzes as q

def test_quiz_update_deprecated():
	# We should get two deprecated warnings
	warn_count = [0]
	def showwarnings( *args ):
		warn_count[0] = warn_count[0] + 1
	orig = warnings.showwarning
	warnings.showwarning = showwarnings

	quiz1 = q.Quiz()
	quiz1.questions['a'] = 1

	quiz2 = q.Quiz()
	quiz2.update( quiz1 )

	assert_that( quiz2.questions, has_entry( 'a', 1 ) )

	quiz2.update( {'Items': {}} )
	assert_that( quiz2.questions, is_( {} ) )

	assert_that( warn_count[0], is_( 2 ) )
	warnings.showwarning = orig

