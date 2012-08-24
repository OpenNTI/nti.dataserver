#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import re

from zope import interface

from nti.contentrendering import plastexids
from nti.contentrendering.resources import interfaces as res_interfaces

from plasTeX import Base
#from plasTex import Command
#from plasTex import DimenCommand
#from plasTex import Environment

class lecture(Base.chapter):
	args = '* [shorttitle] title { label }'

# Parse the frame environment and \frametitle as if it was a \paragraph element 

class frametitle(Base.paragraph):
	pass

# Parses the \frame environment and produces no output.  The childred of
# this environment print as if they were not inside the frame environment.
class frame(Base.Environment):
        args = ' {title:str} [unknown:str]'

        def invoke( self, tex ):
                self.parse(tex)
                return []

# Parses the \columns environment and produces no output.  The childred of
# this environment print as if they were not inside the solumns environment.
class columns(Base.Environment):
        args = '[ pos:str ]'

        def invoke( self, tex ):
                self.parse(tex)
                return []

class column(Base.Command):
        args = '[ pos:str ] width:int'

        def invoke( self, tex ):
                self.parse(tex)
                return []

class mtiny(Base.Command):
        pass

class pause(Base.Command):
	pass

class alert(Base.Command):
	pass

class titlerow(Base.Command):
	pass

class colortabular(Base.Environment):
	pass

class contentwidth(Base.DimenCommand):
	value = Base.DimenCommand.new('600pt')

class alt(Base.Command):
	args = '< overlay > default alternative'

#	def invoke( self, tex ):		
#		_t = self.parse(tex)
#		print("Default is: %s" % self.attributes['default'])
#		print("Alternative is: %s" % self.attributes['alternative'])
#		return []
