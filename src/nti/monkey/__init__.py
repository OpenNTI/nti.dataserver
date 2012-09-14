#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This package contains modules that monkey-patch various parts of the system. Typically they
will do so on import (specified in the name) but will also provide a 'patch' function to avoid
"unused import" warnings. Each module will have minimal dependencies so it can be imported as early as possible.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"
