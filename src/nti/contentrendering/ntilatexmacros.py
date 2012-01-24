#!/usr/bin/env python2.7
#pylint: disable=R0904

from plasTeX import Base


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


def ProcessOptions( options, document ):
	pass
