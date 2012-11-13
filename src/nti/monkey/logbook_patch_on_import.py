#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thanks to :mod:`rq`, we now have a transitive dependency on :mod:`logbook`,
and the last thing we want is to have to deal with multiple logging configurations.

Pyramid/Paster sets up the standard :mod:`logging` configuration based on the ``.ini`` file;
until that changes, we want to effectively ignore :mod:`logbook` altogether. Importing this
module redirects all :mod:`logbook` to the real logging configuration.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

try:
	from logbook.compat import LoggingHandler
	handler = LoggingHandler()
	handler.push_application()
except ImportError:
	handler = None

def patch():
	return handler
