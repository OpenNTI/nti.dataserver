#!/usr/bin/env python2.7
#pylint: disable=R0904

from plasTeX import Base, Command

from plasTeX.Base import Crossref

# Monkey patching time
# SAJ: The following are set to render properly nested HTML.
Base.figure.forcePars = False
Base.minipage.blockType = True
Base.parbox.blockType = True
Base.centerline.blockType = True

class _OneText(Base.Command):
	args = 'text:str'

	def invoke( self, tex ):
		return super(_OneText, self).invoke( tex )

class _Ignored(Base.Command):
	unicode = ''
	def invoke( self, tex ):
		return []

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


class ntiincludevideo(_OneText):
	args = 'text'

	def invoke( self, tex ):
		result = super(ntiincludevideo, self).invoke( tex )
		# change youtube view links to embed
		self.attributes['text'] = self.attributes['text'].textContent.replace( "/watch?v=", '/embed/' )
		return result

class ntipagenum(_OneText):
	pass

class textsuperscript(Base.Command):
	args = 'self'

class textsubscript(Base.Command):
	args = 'self'

class texttrademark(Base.Command):
	unicode = u'\u2122'

class textregistered(Base.Command):
	unicode = u'\u00AE'

class textdegree(Base.Command):
	unicode = u'\u00B0'

# Currency symbols
class yen(Base.Command):
	unicode = u'\xA5'

class eur(Base.Command):
	macroName = 'EUR'
	unicode = u'\x20AC'

class textcent(Base.Command):
	unicode = u'\xA2'

# Handle pdfLatex primatives
class pdfminorversion(Command):
	args = 'version:int'

# Handle latex commands that make no sense in a web layout
class flushbottom(Command):
	args = ''

def ProcessOptions( options, document ):
	pass
