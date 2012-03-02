#!/usr/bin/env python

from ..example_database_initializer import ExampleDatabaseInitializer

import hamcrest

def test_install_quizzes():
	edi = ExampleDatabaseInitializer()
	edi._install_quizzes( {'quizzes': {'quizzes': {}}} )
