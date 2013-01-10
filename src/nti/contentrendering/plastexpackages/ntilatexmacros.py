#!/usr/bin/env python2.7
#pylint: disable=R0904

import hashlib

from plasTeX import Base, Command, Environment

from plasTeX.Base import Crossref

from nti.contentrendering import plastexids
from nti.contentrendering.plastexpackages.graphicx import includegraphics

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
	args = 'video_url'

	def invoke( self, tex ):
		result = super(ntiincludevideo, self).invoke( tex )

		# Set the id of the element
		source = self.source
		_id = hashlib.md5(source.strip().encode('utf-8')).hexdigest()
		setattr( self, "@id", _id )
		setattr( self, "@hasgenid", True )

		# change youtube view links to embed
		self.attributes['video_url'] = self.attributes['video_url'].textContent.replace( "/watch?v=", '/embed/' )
		self.attributes['width'] = 640
		self.attributes['height'] = 360
		_t = self.attributes['video_url'].split('/')
		if 'youtube' in _t[2]:
			self.attributes['service'] = 'youtube'
			self.attributes['video_id'] = _t[len(_t)-1].split('?')[0]
			self.attributes['poster'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/0.jpg'
			self.attributes['thumbnail'] = '//img.youtube.com/vi/' + self.attributes['video_id'] + '/1.jpg'
		return result

class ntiincludeannotationgraphics(includegraphics):
	pass

class ntiincludenoannotationgraphics(includegraphics):
	pass

class ntipagenum(_OneText):
	pass

class ntiglossaryterm(Base.Command):
	args = 'term self'

class ntiimagehref(Base.Command):
	args = 'img url'

class textsuperscript(Base.Command):
	args = 'self'

class textsubscript(Base.Command):
	args = 'self'

# The sidebar environment is to be the base class for other side types such as those from AoPS.
class sidebar(Environment):
	args = 'title'
	blockType = True

# The following 'text' symbols are 'Predefined' LaTeX 2e commands

class textcopyright(Base.Command):
	unicode = u'\u00A9'

class textgreater(Base.Command):
	unicode = u'\u003E'

class textless(Base.Command):
	unicode = u'\u003C'

class textregistered(Base.Command):
	unicode = u'\u00AE'

class texttrademark(Base.Command):
	unicode = u'\u2122'

# The following 'text' symbols are from the textcomp package.

class textapprox(Base.Command):
	unicode = u'\u2248'

class textdegree(Base.Command):
	unicode = u'\u00B0'

class textdiv(Base.Command):
	unicode = u'\u00F7'

class textminus(Base.Command):
	unicode = u'\u2212'

class textpm(Base.Command):
	unicode = u'\u00B1'

class textrightarrow(Base.Command):
	unicode = u'\u2192'

class textsmiley(Base.Command):
	unicode = u'\u263A'

class texttimes(Base.Command):
	unicode = u'\u00D7'

# The following 'text' commands are custom and specific to NTI
class textangle(Base.Command):
	unicode = u'\u2220'

class textcong(Base.Command):
	unicode = u'\u2245'

class textge(Base.Command):
	unicode = u'\u2265'

class textle(Base.Command):
	unicode = u'\u2264'

class textneq(Base.Command):
	unicode = u'\u2260'

class textparallel(Base.Command):
	unicode = u'\u2016'

class textsurd(Base.Command):
	unicode = u'\u221A'

class textperp(Base.Command):
	unicode = u'\u22A5'

class textprime(Base.Command):
	unicode = u'\u2032'

class textsim(Base.Command):
	unicode = u'\u007E'

class textsquare(Base.Command):
	unicode = u'\u25A1'

class texttriangle(Base.Command):
	unicode = u'\u25B3'

class textdoublehyphen(Command):
	unicode = u'\u002D' + u'\u002D'

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

class nobreak(Base.Command):
	args = 'self'

class vfrac(Base.Command):
	args = 'nom denom'

# Misc
class ntivideoroll(Base.Environment,plastexids.NTIIDMixin):
	blockType = True
	_ntiid_cache_map_name = '_ntivideoroll_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'ntivideoroll.'
	_ntiid_type = 'NTIVR'

class ntipreviouspage(Base.Command):
	pass

def ProcessOptions( options, document ):
	pass
