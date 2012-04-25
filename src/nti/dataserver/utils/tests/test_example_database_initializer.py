#!/usr/bin/env python

from ..example_database_initializer import ExampleDatabaseInitializer

import hamcrest
from zope.deprecation import __show__
def test_install_quizzes():
	__show__.off()
	edi = ExampleDatabaseInitializer()
	edi._install_quizzes( {'quizzes': {'quizzes': {}}} )
	__show__.on()
