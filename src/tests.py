import os
import sys
import glob
import argparse
import unittest

from unittest import defaultTestLoader

def load_suite(path, pattern, top_level_dir):
	try:
		suite = defaultTestLoader.discover(path, pattern, top_level_dir)
		print "Test(s) from '%s' loaded" % path
		return suite 
	except Exception, e:
		print "Error importing tests from '%s'. %s" % (path, e)
	except Error, e:
		print "Error importing tests from '%s'. %s" % (path, e)
		
def collect_main_tests(path, pattern="*.py"):
	test_list = []

	def collector(dir):
		for name in os.listdir(dir):
			fd = os.path.join(dir, name)
			if os.path.isdir(fd):
				if name == "tests":
					suite = load_suite(fd, pattern, path)
					if suite: test_list.extend(suite)
				else:
					collector(fd)
	collector(path)

	return test_list
		
def collect_server_tests(path, pattern="test_*.py"):
		 	
	test_list = []
	
	def collector(dir):
		suite = load_suite(dir, pattern, path)
		if suite and suite.countTestCases() == 0:
			for name in os.listdir(dir):
				fd = os.path.join(dir, name)
				if os.path.isdir(fd):
					collector(fd)
		elif suite:
			test_list.extend(suite)
			
	collector(path)
	
	return test_list
	
def test_collector(include_integration=False):
	"""
	Collect all tests return a unittest.TestSuite
	"""

	test_list = []
	src_dir = os.path.realpath(os.path.dirname(__file__))
	main_dir = os.path.join( src_dir, "main/python/nti")
	
	test_list.extend(collect_main_tests(main_dir))
	
	if include_integration:
		tests_dir = os.path.join(src_dir, "test/python/servertests/integration/")
		test_list.extend(collect_server_tests(tests_dir))

	suite = unittest.TestSuite()
	suite.addTests(test_list)
		
	return suite 

test_suite = test_collector

if __name__ == '__main__':
	args = sys.argv[1:]
	include_integration = args[0] == '--include_integration' if args else False
	test_collector(include_integration)
