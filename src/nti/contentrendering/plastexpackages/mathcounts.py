#!/usr/bin/env python
from __future__ import print_function, unicode_literals


# Disable pylint warning about "too many methods" on the Command subclasses,
# and "deprecated string" module
#pylint: disable=R0904,W0402


from plasTeX.Base import chapter

class mathcountschapter( chapter ):
	args = '* [ toc ] title img'
