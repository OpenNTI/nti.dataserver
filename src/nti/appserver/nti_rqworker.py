#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A entry point to help us ensure that we are loading rqworkers
along w/ the dataserver code

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys

from rq.scripts import rqworker

from nti.dataserver.utils import run_with_dataserver

def _run_worker():
	rqworker.main()

def main():
	exe = sys.argv[0]
	args = sys.argv[1:]
	if not args:
		raise Exception('Specify a dataserver environment root directory')

	env_dir = args[0]
	sys.argv = [exe] + args[1:]
	run_with_dataserver(environment_dir=env_dir,
						function=lambda: _run_worker())
	sys.exit(0)


if __name__ == '__main__':
	main()
