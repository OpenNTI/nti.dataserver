#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A entry point to help us ensure that we are loading rqworkers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys

from rq.scripts import rqworker

def _run_worker():
	rqworker.main()

def main():
	_run_worker()
	sys.exit(0)

if __name__ == '__main__':
	main()
