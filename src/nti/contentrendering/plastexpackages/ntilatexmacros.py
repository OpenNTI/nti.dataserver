#!/usr/bin/env python2.7
#pylint: disable=R0904

from plasTeX import Base, Command

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

# Handle pdfLatex primatives
class pdfminorversion(Command):
	args = 'version:int'

# Handle latex commands that make no sense in a web layout
class flushbottom(Command):
	args = ''

def ProcessOptions( options, document ):
	pass
