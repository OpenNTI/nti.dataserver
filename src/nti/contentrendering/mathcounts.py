from plasTeX import Base


def _digestAndCollect( self, tokens, until ):
	self.digestUntil(tokens, until )
	# Force grouping into paragraphs to eliminate the empties
	if getattr(self, 'forcePars', True):
		self.paragraphs()

class mathcountsyear(Base.chapter):
	pass

class mathcountsworksheet(Base.section):
	args = Base.section.args + ' NTIID:str'


	forcePars = True

	def digest(self, tokens):
		self.paragraphs()
		super(mathcountsworksheet,self).digest( tokens )


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
	pass

class mathcountsresult(Base.Environment):
	pass

class mathcountssolution(Base.Environment):
	pass

class mathcountshint(Base.Command):
	args = 'href:str helptext:str'

class tab(Base.Command):
	pass

from plasTeX.Base import Math

#The math package does not correctly implement the sqrt macro.  It takes two args
Math.sqrt.args='[root]{arg}'

#inlineMathTypes=['svg',  'mathjax_inline']
#displayMathTypes=['svg', 'mathjax_display']

inlineMathTypes = ['mathjax_inline']
displayMathTypes = ['mathjax_display']

Math.math.resourceTypes = inlineMathTypes
#Math.ensuremath.resourceTypes=inlineMathTypes

Math.displaymath.resourceTypes = displayMathTypes
#Math.equation.resourceTypes=displayMathTypes
#Math.eqnarray.resourceTypes=displayMathTypes
#Math.EqnarrayStar.resourceTypes=displayMathTypes


#TODO this xymatrix junk is not right but it allows us to get past it for now
class xymatrix(Base.Command):
	args='text:str'

#from plasTeX.Packages.fancybox import *

from plasTeX.Packages.graphicx import includegraphics
from plasTeX.Packages.amsmath import align, AlignStar, alignat, AlignatStar, gather, GatherStar

align.resourceTypes = displayMathTypes
AlignStar.resourceTypes = displayMathTypes
alignat.resourceTypes = displayMathTypes
AlignatStar.resourceTypes = displayMathTypes
gather.resourceTypes = displayMathTypes
GatherStar.resourceTypes = displayMathTypes

#from plasTeX.Packages.multicol import *

#includegraphics.resourceTypes = ['png', 'svg']
includegraphics.resourceTypes = ['png']

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
