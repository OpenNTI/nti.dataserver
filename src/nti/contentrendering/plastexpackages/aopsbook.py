from plasTeX import Base
import re




class _OneText(Base.Command):
	args = 'text:str'

	def invoke( self, tex ):
		return super(_OneText, self).invoke( tex )

class _Ignored(Base.Command):
	unicode = ''
	def invoke( self, tex ):
		return []

#
# Presentation things to ignore
#

class rindent(_Ignored):
	pass

class vupnud(_Ignored):
	pass

class pagebreak(_Ignored):
	pass

#TODO:  In many cases phantom is used purely for spacing we don't care about
#in our rendering.  At other times it's used for spaceing we do need to render (e.g. fill in the blank style blanks)
#This looks like it will be a case by case basis.
#included phantom doesn't allow for tex fragments as args
class phantom(Base.Space.phantom):
	args = 'tex'
	pass

class yen(Base.Command):
	unicode = u'\xA5'
	pass

class textcent(Base.Command):
	unicode = u'\xA2'
	pass

class Cube(_OneText):
	resourceTypes = ['png', 'svg']
	pass

class BlackCube(Cube):
	pass

class picskip(Base.Command):
	args = ' {text:int} '

	def invoke( self, tex ):
		# There's a {0} or so with this that we need to discard too
		# TODO: This may not be the best way
		tex.readGrouping( '{}' )
		return []

	def digest( self, tokens ):
		return super(picskip,self).digest( tokens )

## class newline(Base.Command):
##	macroName = '\\'

##	def toXML(self):
##		return '<newline/>'

def digestUntilNextTextSize(self, tokens):
	return _digestAndCollect( self, tokens, Base.FontSelection.TextSizeDeclaration )

Base.FontSelection.TextSizeDeclaration.digest=digestUntilNextTextSize



class rule(Base.Boxes.rule):
	""" Rules have no place in this DOM, except in math mode, where their presentation
	can be important (e.g., the rlin macro)."""
	def invoke( self, tex ):
		superResult = super(rule,self).invoke( tex )
		if self.ownerDocument.context.isMathMode:
			if self.ownerDocument.context.contexts[-1].parent.name == 'array':
				# One exception is when they use rules inside arrays
				# to try to extend an hline. mathjax rendering doesn't
				# need this, and I didn't see it being helpful in
				# their PDF either
				return []
			return superResult
		return []

class vspace(Base.Space.vspace):
	def invoke( self, tex ):
		super( vspace, self ).invoke( tex )
		return []

class vskip(Base.Primitives.vskip):
	def invoke( self, tex ):
		super( vskip, self ).invoke( tex )
		return []

class chapterpicture(_OneText):
	def invoke( self, tex ):
		super(chapterpicture,self).invoke( tex )
		return []

# FIXME: Chapterauthor and chapterquote are included
# BEFORE the \chapter marker, and so get digested into the
# PREVIOUS section in the DOM, not the chapter they belong too.
# Maybe these can just be discarded?

class chapterquote(Base.Command):
	args = ''

	def invoke( self, tex ):
		#TODO: Can we read the next command, which should be the
		#\chapterauthor and add that as a child node?
		tokens, source = tex.readGrouping( '{}', expanded=True, parentNode=self)
		self += tokens
		return None

class chapterauthor(Base.Command):
	args = ''

	def invoke( self, tex ):
		self += tex.readGrouping( '{}', expanded=True, parentNode=self)[0]
		return None


class Def(_OneText):
	pass

class Defnoindex(_OneText):
	args = 'text'

class defn(Base.Environment):
	pass

class defns(Base.Environment):
	pass

class picdefns(defns):
	args = '{Picture}'
	pass

class cancel(Base.Command):
	args = 'text'

class cancelto(Base.Command):
	args = 'to text'

#TODO:  Inherit from something in Boxes.py?
class boxed(Base.Command):
	args = '{self}'

class text(Base.BoxCommand):

	args = '{self}'

	def __init__(self):
		self.arguments[0].options['stripLeadingWhitespace']=True

	def parse(self, tex):
		return super(text, self).parse(tex)

	def invoke( self, tex ):
		return super(text,self).invoke( tex )


#TODO does this get handled like ^
class textsuperscript(Base.Command):
	args = 'text:str'
	pass

#We would like to be able to normalize math mode
#at parse time such that expressions like $24$ automatically
#become simple text nodes, but that's not (easily) possible: we cannot
#make that decision until after the children are parsed, and by then
#we're in the DOM (the digest() method does not yet have the proper parentNode)
#to remove

class angle(Base.Command):

	def invoke( self, tex ):
		super(angle, self).invoke(	tex )


# The rlin command and the vv command break rendering of
# vectors, so they are disabled.
# class rlin(Base.Command):
#	""" A presentation command that means overleftrightarrow """
#	args = ''

#	def invoke( self, tex ):
#		arrow = self.ownerDocument.createElement( 'overleftrightarrow' )
#		expr = tex.readGrouping( '{}', expanded=True, parentNode=arrow)[0]
#		arrow += expr
#		return [arrow]

#class vv(Base.Command):
#	""" A vector from esvect. We simplify to the common overrightarrow """
#
#	args = ''
#
#	def invoke( self, tex ):
#		arrow = self.ownerDocument.createElement( 'vec' )
#		expr = tex.readGrouping( '{}', expanded=True, parentNode=arrow)[0]
#		arrow += expr
#		return [arrow]


## rlin is re-enabled for the sake of mathjax
class rlin(Base.Command):
	""" A presentation command that means overleftrightarrow. However,
	we represent it in the DOM for MathJax--it needs to get the
	grouping around the text. This corresponds to a custom macro in
	the default-layout.html AoPS template. """
	args = '{text}'

	def invoke( self, tex ):
		return super(rlin,self).invoke( tex )

# Attributions
class source(Base.Command):
	args = '{source:str}'
	pass

class MathCounts(source):
	args = ''
	def invoke(self, tex):
		res = super(MathCounts, self).invoke(tex)
		self.attributes['source'] = 'MATHCOUNTS'
		return res

class MOEMS(source):
	args = ''
	def invoke(self, tex):
		res = super(MOEMS, self).invoke(tex)
		self.attributes['source'] = 'MOEMS'
		return res

class AMC(source):
	args = '{text:str}'
	def invoke(self, tex):
		res = super(AMC, self).invoke(tex)
		self.attributes['source'] = 'AMC %s' % self.attributes['text']
		return res

# Counters
class partnum(Base.Command):
	unicode = ''

class parts(Base.List):

	counters = ['partnum']
	args = '[ init:int ]'

	def invoke( self, tex ):
		res = super(parts, self).invoke( tex )

		if 'init' in self.attributes and self.attributes['init']:
			self.ownerDocument.context.counters['partnum'].setcounter( self.attributes['init'] )
		elif self.macroMode != Base.Environment.MODE_END:
			self.ownerDocument.context.counters['partnum'].setcounter(0)

	def digest( self, tokens ):
		#After digesting loop back over the children moving nodes before
		#the first item into the first item
		res = super(parts, self).digest(tokens)
		if self.macroMode != Environment.MODE_END:
			nodesToMove = []

			for node in self:

				if isinstance(node, Base.List.item):
					nodesToMove.reverse()
					for nodeToMove in nodesToMove:
						self.removeChild(nodeToMove)
						node.insert(0, nodeToMove)
					break

				nodesToMove.append(node)

		return res




class part(Base.List.item):
	#Ordinary list items can accept a value, this may or may not be used in AoPS code
	#args = ''

	def invoke( self, tex ):
		self.counter = 'partnum'
		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Command.invoke(self,tex)


	def digest( self, tex ):
		super( part, self ).digest( tex )

class parthard(part):
	pass

#Exercises exist at the end of a section and are started with \exercises.  There is
#no explicit stop.	Exercises end when a new section starts
class exnumber(Base.Command):
	unicode = ''

class exercises(Base.subsection):
	args = ''
	counter= ''

	#this is used to emulate a list.  Like parts we need to make sure
	#that the first child in the list is  an exer or exerhard
	def digest( self, tokens ):
		#After digesting loop back over the children moving nodes before
		#the first item into the first item
		res = super(exercises, self).digest(tokens)
		if self.macroMode != Environment.MODE_END:

			nodesToMove = []

			for node in self:

				if isinstance(node, exer):
					nodesToMove.reverse()
					for nodeToMove in nodesToMove:
						self.removeChild(nodeToMove)
						node.insert(0, nodeToMove)
					break

				nodesToMove.append(node)

		return res

class exer(Base.subsubsection):
	args = ''
	counter='exnumber'

	def invoke( self, tex ):
		res = super(exer,self).invoke( tex )

		self.attributes['exnumber'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['section'].value) + '.' + str(self.ownerDocument.context.counters['exnumber'].value)

		return res

	def postParse(self, tex):
		super(exer, self).postParse(tex)

		#Because we are a subsubsection our deep section level causes the ref
		#attribute to not be set in the super.	In a section with a lower sec number
		#(I.E. subsection, section, chapter...) the super would also set a captionName attribute
		self.ref = self.ownerDocument.createElement('the'+self.counter).expand(tex)
		self.captionName = self.ownerDocument.createElement(self.counter+'name').expand(tex)


class dfrac(Base.Command):
	args = 'num den'

class exerhard(exer):
	pass

class bogus(Base.Environment):
	pass

class importantdef(Base.Environment):
	pass

class important(Base.Environment):
	pass

class concept(Base.Environment):
	pass

class warning(Base.Environment):
	pass

class game(Base.Environment):
	pass

class sidebar(Base.Environment):
	pass

class xtra(Base.Environment):
	pass

titlepattern = re.compile(r'/Title\s+\((?P<title>.*?)\)\s+/Author\s+\((?P<authors>.*?)\).*')

class pdfinfo(Base.Command):
	args = 'info:str'

	#we want to do something intelligent with the argument to pdfinfo
	#For now we set the title of the document, but we may also want
	#to do something intelligent with the author
	def invoke(self, tex):
		res = super(pdfinfo, self).invoke( tex )

		if 'info' in self.attributes:
			match = titlepattern.match(self.attributes['info'])
			title = match.group('title')
			authors = match.group('authors')

			self.ownerDocument.userdata['title'] = title
			self.ownerDocument.userdata['authors'] = authors

		return res;

from plasTeX.Base import Crossref

#TODO do pagerefs even make sense in our dom?
#Try to find an intelligent page name for the reference
#so we don't have to render the link text as '3'
class pageref(Crossref.pageref):

	#we would hope to generate the pagename attribute in
	#the invoke method but since it is dependent on the page
	#splits used at render time we define a function to be called
	#from the page template
	def getPageNameForRef(self):
		#Look up the dom tree until we find something
		#that would create a file
		fileNode = self.idref['label']
		while not getattr(fileNode, 'title', None) and getattr(fileNode, 'parentNode', None):
			fileNode = fileNode.parentNode

		if hasattr(fileNode, 'title'):
			return getattr(fileNode.title, 'textContent', fileNode.title)

		return None

class probref(Crossref.ref):
	pass

class _BasePicProblem(Base.Environment):
	args = 'pic'
	counter = 'probnum'
	def invoke(self,tex):
		res = super(_BasePicProblem,self).invoke( tex )

		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)

		#if self.macroMode != Base.Environment.MODE_END:
		#	self.refstepcounter(tex)
		# Move from the argument into the DOM
		if 'pic' in self.attributes:
			self.appendChild( self.attributes['pic'] )
		return res

class picproblem(_BasePicProblem):
	pass

class picproblemspec(picproblem):
	pass

class picsecprob(_BasePicProblem):
	pass

import pdb

class problem(Base.Environment):
	args = '[unknown]'
	counter = 'probnum'
	forcePars = True
	blockType = True

	def invoke( self, tex ):
		#if self.macroMode != Base.Environment.MODE_END:
		#	self.refstepcounter(tex)


		res = super(problem,self).invoke( tex )
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)
		return res


class problemspec(problem):
	pass

def _digestAndCollect( self, tokens, until ):
	self.digestUntil(tokens, until )
	# Force grouping into paragraphs to eliminate the empties
	if getattr(self, 'forcePars', True):
		self.paragraphs()

from plasTeX.Base import Node
class sectionproblems(Base.subsection):
	counter = 'sectionprobsnotused'
	args = ''

	def invoke( self, tex ):
		self.ownerDocument.context.counters['saveprobnum'].setcounter(
			self.ownerDocument.context.counters['probnum'] )
		return super(sectionproblems,self).invoke( tex )

	def digest(self, tokens):
		_digestAndCollect( self, tokens, nomoresectionproblems )

		#Adapted from Environment.paragraphs
		for i in range(len(self)-1, -1, -1):
			item = self[i]
			# Filter out any empty paragraphs
			if item.level == Node.PAR_LEVEL:
				if len(item) == 0:
					self.pop(i)
				elif len(item) == 1 and item[0].isElementContentWhitespace:
					self.pop(i)

			#Filter out any whitespace text nodes
			elif item.nodeType == Node.TEXT_NODE:
				if item.isElementContentWhitespace:
					self.pop(i)

		#For some reason we can't combine this with the loop above previousSibling isn't correct
		for i in range(len(self)-1, -1, -1):
			item = self[i]

			if not ( isinstance(item, problem) or isinstance(item, _BasePicProblem) ):
				before = item.previousSibling;
				if before is not None:
					self.pop(i)
					before.append(item)
				else:
					log.warning('Non problem item %s of %s has no previous sibling' % (item, self))



class picsecprobspec(_BasePicProblem):
	pass

class picproblemspec(_BasePicProblem):
	pass

class secprob(problem):
	pass

class nomoresectionproblems( Base.Command ):

	blockType = True

	def invoke( self, tex ):
		self.ownerDocument.context.counters['probnum'].setcounter(
			self.ownerDocument.context.counters['saveprobnum'] )
		return super(nomoresectionproblems,self).invoke(tex)

class beginsol( Base.subsection ):
	args = ''
	counter = ''

	def invoke( self, tex ):
		res = super(solution, self).invoke(tex)

		#We encounter solutions right after the problem therefore our
		#solutions probnum should be the current value of the probnum counter
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)

		return res

	def digest( self, tokens ):
		_digestAndCollect( self, tokens, stopsol )

class stopsol( Base.Command ):
	pass

class solution( Base.Environment ):
	args = ''
	blockType = True
	forcePars = True

	def invoke( self, tex ):
		res = super(solution, self).invoke(tex)

		#We encounter solutions right after the problem therefore our
		#solutions probnum should be the current value of the probnum counter
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)

		return res

# FIXME: These counters are not right?
# If we don't override the args attribute, these consume one letter of text
class reviewprobs(Base.section):
	args = ''
	#counter = 'probnum'

	def invoke(self, tex):
		#pdb.set_trace();
		#Attach a title to this "section"
		docFragment = self.ownerDocument.createDocumentFragment();
		docFragment.appendText(["Review Problems"]);
		self.title=docFragment;

		#Save the probnum counter b/c it gets reset in the super
		self.ownerDocument.context.counters['saveprobnum'].setcounter(
			self.ownerDocument.context.counters['probnum'] )

		res = super(reviewprobs, self).invoke(tex);

		#Restore the probnum counter
		self.ownerDocument.context.counters['probnum'].setcounter(
			self.ownerDocument.context.counters['saveprobnum'] )

		return res;

class challengeprobs(Base.section):
	args = ''
	#counter = 'probnum'
	def invoke(self, tex):
		#pdb.set_trace()
		docFragment = self.ownerDocument.createDocumentFragment();
		docFragment.appendText(["Challenge Problems"]);
		self.title=docFragment;

		#Save the probnum counter b/c it gets reset in the super
		self.ownerDocument.context.counters['saveprobnum'].setcounter(
			self.ownerDocument.context.counters['probnum'] )

		res = super(challengeprobs, self).invoke(tex);

		#Restore the probnum counter
		self.ownerDocument.context.counters['probnum'].setcounter(
			self.ownerDocument.context.counters['saveprobnum'] )

		return res;


class revprob(Base.subsection):
	args = ''
	counter = 'probnum'

	def invoke( self, tex ):
		res = super(revprob,self).invoke( tex )
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)
		return res

class chall(Base.subsection):
	args = ''
	counter = 'probnum'

	def invoke( self, tex ):
		res = super(chall,self).invoke( tex )
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)
		return res

class challhard(Base.subsection):
	args = ''
	counter = 'probnum'

	def invoke( self, tex ):
		res = super(challhard,self).invoke( tex )
		self.attributes['probnum'] = str(self.ownerDocument.context.counters['chapter'].value) + '.' + str(self.ownerDocument.context.counters['probnum'].value)
		return res
# This is all handled by the main driver
from plasTeX.Base import Arrays
# tabularTypes = ['png', 'svg']

# Arrays.tabular.resourceTypes = tabularTypes
# Arrays.TabularStar.resourceTypes = tabularTypes
# Arrays.tabularx.resourceTypes = tabularTypes

from plasTeX.Base import Math


# #The math package does not correctly implement the sqrt macro.	It takes two args
# Math.sqrt.args='[root]{arg}'

# inlineMathTypes = ['mathjax_inline']
# displayMathTypes = ['mathjax_display']

# #inlineMathTypes = ['mathjax_inline', 'png', 'svg']
# #displayMathTypes = ['mathjax_display', 'png', 'svg']

# Math.math.resourceTypes = inlineMathTypes
# #Math.ensuremath.resourceTypes=inlineMathTypes

# Math.displaymath.resourceTypes = displayMathTypes
# Math.EqnarrayStar.resourceTypes = displayMathTypes
# #Math.equation.resourceTypes=displayMathTypes
#Math.eqnarray.resourceTypes=displayMathTypes
#Math.EqnarrayStar.resourceTypes=displayMathTypes


#for \nth, \nst, \nrd, etc..
class nsuperscript(Base.Command):
	args = 'text'

	## #We need to store if we are inside math mode
	## def invoke(self, tex):
	## 	result = super(nsuperscript, self).invoke( tex )
	## 	self.insideMathElement = self.ownerDocument.context.isMathMode
	## 	return result

	## #We want to be treated as math for resource generation and rendering
	## #so our source needs to make us look like a math element.  if we are
	## #contained in a math element we get that for free.	If not we have to put
	## #ourselves in math mode using $$
	## @property
	## def source(self):
	## 	mySource = super(nsuperscript, self).source

	## 	if not self.insideMathElement:
	## 		#If we wrap our self in math environment
	## 		#we need to make sure we don't already contain math
	## 		mySource = '$%s$' % mySource

	## 	return mySource

class nst(nsuperscript):
	pass

class nnd(nsuperscript):
	pass

class nrd(nsuperscript):
	pass

class nth(nsuperscript):
	pass


# FIXME: star imports!
from plasTeX.Packages.fancybox import *

from plasTeX.Packages.graphicx import *

from plasTeX.Packages.amsmath import *

# align.resourceTypes = displayMathTypes
# AlignStar.resourceTypes = displayMathTypes
# alignat.resourceTypes = displayMathTypes
# AlignatStar.resourceTypes = displayMathTypes
# gather.resourceTypes = displayMathTypes
# GatherStar.resourceTypes = displayMathTypes

# from plasTeX.Packages.multicol import *

# #includegraphics.resourceTypes = ['png', 'svg']
# includegraphics.resourceTypes = ['png']

class rightpic(includegraphics):
	" For our purposes, exactly the same as an includegraphics command. "
	packageName = 'aopsbook'

class leftpic(rightpic):
	pass


class parpic(Base.Command):
	args = '( size:dimen ) ( offset:dimen ) [Options:str] [Position] {Picture}'

	def invoke(self, tex):
		res = super( parpic, self).invoke(tex)

		return res


class fig(Base.figure):
	pass

class negthinspaceshorthand(Base.Text.negthinspace):
	macroName = '!'
	pass

## Hints
class hints(_Ignored):
	pass

class hint(Crossref.label):

	def invoke( self, tex ):
		res = super( hint, self ).invoke( tex )
		return res

class thehints(Base.List):
	# We keep counters but ignore them
	counters = ['hintnum']
	args = ''

	def invoke( self, tex ):
		res = super(thehints, self).invoke( tex )

		if self.macroMode != Base.Environment.MODE_END:
			self.ownerDocument.context.counters['hintnum'].setcounter(0)

	def digest( self, tokens ):
		super(thehints,self).digest( tokens )
		# When we end the hints, go back and fixup the references and
		# move things into the dom. Remember not to iterate across
		# self and mutate self at the same time, hence the copy
		nodes = list(self.childNodes)
		for child in nodes:
			if child.idref and child.idref['label'] and \
				   type(child.idref['label']).__module__ == 'aopsbook':
				# we are the current parent, the label needs to be the
				# new parent
				self.removeChild( child )
				child.idref['label'].appendChild( child )
			else:
				# for now, if it doesn't refer to anything, delete it
				self.removeChild( child )


class hintitem(Crossref.ref):
	args = 'label:idref'

	def invoke( self, tex ):
#		self.counter = 'hintnum'
#		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Command.invoke(self,tex)

	def digest(self, tokens):
		_digestAndCollect( self, tokens, hintitem )

class ntirequires(Base.Command):
	args = 'rels:dict'

	def toXML(self):
		"""
		<nti:topic rdf:about='...'>
		  <nti:requires><aops:concept>...</aops:concept></nti:requires>
		"""
		rels = self.attributes['rels']
		xml = "<nti:topic rdf:about='" + self.findContainer() + "'>"
		for key in rels:
			xml += "<nti:requires><aops:concept>" + key + "<aops:concept><nti:requires>"
		xml += "</nti:topic>"
		return xml

	def findContainer(self):
		# parent node should have the 'title' attribute
		result = ""
		parentNode = self.parentNode
		while parentNode:
			if hasattr(parentNode.attributes,'title'):
				result = parentNode.attributes['title']
				break
			parentNode = parentNode.parentNode
		return result

from plasTeX.Base.LaTeX import Index
###
### Indexes in math equations turn out to mess up
### mathjax rendering. Thus we remove them.
class index(Index.index):

	def invoke(self, tex):
		result = super(index,self).invoke( tex )
		if self.ownerDocument.context.isMathMode:
			self.ownerDocument.userdata['index'].pop()
			result = []
		return result

def ProcessOptions( options, document ):

	document.context.newcounter( 'exnumber' , resetby='section')

	document.context.newcounter( 'partnum' )

	# used in \begin{problem}.
	# TODO: Get this to reset in chapters (probably not important)
	document.context.newcounter( 'probnum' , resetby='chapter')

	# With customising the paths, we could use absolotue paths and fix
	# the temporary directory issue? Really only important for direct
	# HTML rendering
	document.userdata.setPath( 'packages/aopsbook/paths', ['.', '../Images/'])
	document.userdata.setPath( 'packages/graphicx/paths', ['.', '../Images/'])

	# AoPS uses fully qualified image names, so we don't want to
	# search for multiple extensions; that really slows things down
	# since it spawns an external program (1 mi nvs 20 secs)
	document.userdata.setPath( 'packages/graphicx/extensions',
							   [] )
	document.userdata.setPath( 'packages/aopsbook/extensions', [])

	# hints
	document.context.newcounter( 'hintnum' )

	document.context.newcounter('sectionprobsnotused')
	document.context.newcounter('challprobsnotused');
	document.context.newcounter('reviewprobsnotused')



