#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Versions of :mod:`webob.cookie` up through at least 1.2.3 are overly
aggressive when it comes to escaping the values of the Set-Cookie
header. This is fixed in 1.3 so this patch does nothing there.

According to `RFC 6265 <http://tools.ietf.org/html/rfc6265#section-4.1.1>`, only a few values
have to be escaped: control characters, double quote, comma, semicolon, and backslash. Notably, the at-sign, @, is
allowed. However, webob leaves this on its list.

Importing this module (and calling patch) adjusts the webob cookie
functions to not escape these values.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import pkg_resources

# In fact we require running on 1.3, which changes
# the implementation...sadly, the __version__ attribute
# did not change from 1.2.3 to 1.3. So we use
# the brute-force method to check
dist = pkg_resources.get_distribution('webob')
if not dist.version or dist.version < '1.3':
	raise ImportError("WebOb less that 1.3 is no longer supported: %s" % dist)

def patch():
	pass

patch()
