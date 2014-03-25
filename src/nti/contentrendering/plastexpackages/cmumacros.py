#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CMU macros

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Base
from plasTeX.Base import ColumnType

class _Ignored(Base.Command):
	unicode = ''

	def invoke(self, tex):
		return []

class lecture(Base.chapter):
	args = '* [shorttitle] title { label }'

# Parse the frame environment and \frametitle as if it was a \paragraph element 

class frametitle(Base.paragraph):
	pass

# Parses the \frame environment and produces no output.  The childred of
# this environment print as if they were not inside the frame environment.
class frame(Base.Environment):
	args = ' {title:str} [unknown:str]'

	def invoke(self, tex):
		self.parse(tex)
		return []

# Parses the \columns environment and produces no output.  The childred of
# this environment print as if they were not inside the solumns environment.
class columns(Base.Environment):
	args = '[ pos:str ]'

	def invoke(self, tex):
		self.parse(tex)
		return []

class column(Base.Command):
	args = '[ pos:str ] width:int'

	def invoke(self, tex):
		self.parse(tex)
		return []

class framebreak(_Ignored):
	pass

class noframebreak(_Ignored):
	pass

class mtiny(Base.Command):
		pass

class pause(Base.Command):
	pass

class alert(Base.FontSelection.TextCommand):
	args = '< overlay > self'

class colortabular(Base.Environment):
	pass

class contentwidth(Base.DimenCommand):
	value = Base.DimenCommand.new('600pt')

class beamertemplatebookbibitems(_Ignored):
	pass

class beamertemplatearticlebibitems(_Ignored):
	pass

class alt(Base.Command):
	args = '< overlay > default alternative'

# Custom column type for CMU tables
ColumnType.new(str('Y'), {'text-align':'left'})
ColumnType.new(str('k'), {'text-align':'left', 'background-color': '#cccccc'}, args='width:str')

# Custom command to for title row color
class titlerow(Base.Command):
	args = '[ space ]'

	def digest(self, tokens):
		super(titlerow, self).digest(tokens)
		node = self.parentNode.parentNode
		node.rowspec['background-color'] = '#cccccc'

# Custom commands for use with the algorithm2e environment
class Label(Base.Command):
	blockType = True
	args = 'self'

class Goto(Base.Command):
	blockType = True
	args = 'self'

class Procedure(Base.Command):
	blockType = True
	args = 'self'

class Input(Base.Command):
	blockType = True
	args = 'self'
