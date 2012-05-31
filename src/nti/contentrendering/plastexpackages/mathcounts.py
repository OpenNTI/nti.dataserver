#!/usr/bin/env python
from __future__ import print_function, unicode_literals


# Disable pylint warning about "too many methods" on the Command subclasses,
# and "deprecated string" module
#pylint: disable=R0904,W0402


from plasTeX import Base

# FIXME: Necessary to re-export these? See FIXME in aopsbook
from plasTeX.Packages.graphicx import includegraphics
from plasTeX.Packages.amsmath import align, AlignStar, alignat, AlignatStar, gather, GatherStar

def _digestAndCollect( self, tokens, until ):
	self.digestUntil(tokens, until )
	# Force grouping into paragraphs to eliminate the empties
	if getattr(self, 'forcePars', True):
		self.paragraphs()

class mathcountsyear(Base.chapter):
	pass

class mathcountsworksheet(Base.section):
	# TODO: Now that nti_render is doing meaningful things with
	# the 'id' (\label) and title to create unique NTIIDs, we can
	# probably drop the need to specify this? That may depend on how
	# quizzes get extracted at runtime?
	args = Base.section.args + ' NTIID:str'

	forcePars = True

	def digest(self, tokens):
		self.paragraphs()
		super(mathcountsworksheet,self).digest( tokens )
		self.id = self.attributes['NTIID']

class mathcountsdifficulty(Base.Environment):
	pass

class mathcountsproblem(Base.Environment):
	# Within a mathcounts handbook, the problems are numbered
	# sequentially, even across sections.
	counter = 'probnum'
	def invoke(self, tex):
		res = super(mathcountsproblem, self).invoke(tex)
		self.attributes['probnum'] = self.ownerDocument.context.counters['probnum'].value
		self.paragraphs()
		return res

class mathcountsquestion(Base.Environment):
	counter = 'questionnum'
	def invoke(self, tex):
		res = super(mathcountsquestion, self).invoke(tex)
		self.attributes['questionnum'] = self.ownerDocument.context.counters['questionnum'].value
		self.paragraphs()
		return res

class mathcountsresult(Base.Environment):
	pass

class mathcountssolution(Base.Environment):
	pass

class sidebar(Base.Environment):
	pass

class mathcountshint(Base.Command):
	args = 'href:str helptext:str'

class tab(Base.Command):
	pass


#TODO this xymatrix junk is not right but it allows us to get past it for now
class xymatrix(Base.Command):
	args = 'text:str'


class rightpic(includegraphics):
	"For our purposes, exactly the same as an includegraphics command. "
	packageName = 'mathcounts'

class leftpic(rightpic):
	pass

## Parpic takes more arguments than rightpic/includegraphics does. If we don't
## parse them, we get yick in the DOM/HTML
class parpic(includegraphics):
	args = '* [ options:dict ] file:str'


def ProcessOptions( options, document ):
	# In a mathcounts handbook, the problem numbers are sequential throughout
#	document.context.newcounter( 'probnum', resetby='section')
	document.context.newcounter( 'solnum' )
