#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from nti.contentrendering import plastexids
from nti.contentrendering.plastexpackages.graphicx import includegraphics
from nti.contentrendering.plastexpackages.ntiassessment import _LocalContentMixin
from plasTeX.Base import Command, Crossref, Environment, List

NTIID_TYPE = 'NSD'

def _timeconvert( timestring ):
	"""Convert a time in the form HH:MM:SS, with hours and minutes optional, to seconds."""
	_t = timestring.split(':')
	t_out = 0
	if len(_t) == 3:
		if int(_t[1]) >= 60 or int(_t[2]) >= 60:
			raise ValueError('Invalid time in %s' % timestring)
		t_out = int(_t[0]) * 3600 + int(_t[1]) * 60 + float(_t[2])
	elif len(_t) == 2:
		if int(_t[1]) >= 60:
			raise ValueError('Invalid time in %s' % timestring)
		t_out = int(_t[0]) * 60 + float(_t[1])
	elif len(_t) == 1:
		t_out = float(_t[0])
	else:
		raise ValueError('Invalid time in %s' % timestring)
	return t_out

class ntislidedeckname(Command):
	pass

class ntislidedeck(List, plastexids.NTIIDMixin):
	"""The ntislidedeck environment represents a "PowerPoint" style presentation. The environment consists of a list of references to slides located elsewhere in the content. This allows the slide deck to be handled separately from the indivual slides.  The ability to do this is important since individual slides will be displayed in the content when viewed in the normal reading mode, where as the slide deck construct is only displayed when you enter the slide deck mode of the application.

	*** This is not used right now ***

	\begin{ntislidedeck}
	    \ntislideref{slidelabel}
	    \ntislideref{slidelabel}
	    \ntislideref{slidelabel}
	    \ntislideref{slidelabel}
	\end{ntislidedeck}

	\begin[id=presintationId]{ntislidedeck}
	\end{ntislidedeck}
"""

	counter = "ntislidedeck"
	blockType = True

	class ntislideref(Crossref.ref):
		pass

class ntislidevideoname(Command):
        unicode = ''

class ntislidevideo(Environment):
	"""This environment encapsulates ntiincludevideo objects so that we can tag them with a label and reference them elsewhere.
"""
	counter = "ntislidevideo"
	blockType=True

	def digest(self, tex):
		super(ntislidevideo, self).digest(tex)
		video = self.getElementsByTagName( 'ntiincludevideo' )[0]
		self.type = video.attributes['service']
		self.provider_id = video.attributes['video_id']
		self.thumbnail = video.attributes['thumbnail']
		self.video_url = video.attributes['video_url']
		self.id = video.id

class ntislidename(Command):
        unicode = ''

class ntislide(_LocalContentMixin, Environment, plastexids.NTIIDMixin):
	"""The ntislide environment represents a single slide from a "PowerPoint" style presentation. 

	\begin{ntislide}
	    \ntislidetitle{title}
	    \ntislideimage{imagepath}
	    \ntislidevideoref[start=time,stop=time]{video label}
	    \begin{ntislidetext}
	        Arbitrary text goes here
	    \end{ntislidetext}
	\end{ntislide}
"""
	args = '[ options:dict ]'
	counter = "ntislide"
	blockType = True
	_ntiid_cache_map_name = '_ntislide_ntiid_map'
        _ntiid_allow_missing_title = True
        _ntiid_suffix = 'nsd.'
        _ntiid_title_attr_name = 'ref'
	_ntiid_type = NTIID_TYPE

	def invoke(self, tex):
		_t = super(ntislide, self).invoke(tex)
		if 'options' not in self.attributes or not self.attributes['options']:
			self.attributes['options'] = {}
		if 'presentationonly' not in self.attributes['options']:
			self.attributes['options']['presentationonly'] = False
		else:
			self.style['display'] = 'none'
		return _t

	def digest(self, tex):
		super(ntislide, self).digest(tex)
		self.slidenumber = self.ownerDocument.context.counters[self.counter].value

	class ntislidetitle(Command):
		args = 'title'

		def digest(self, tex):
			super(ntislide.ntislidetitle, self).digest(tex)
			self.parentNode.title = self.attributes['title']

	class ntislideimage(includegraphics):

		def digest(self, tex):
			super(ntislide.ntislideimage, self).digest(tex)
			self.parentNode.slideimage = self

	class ntislidevideoref(Crossref.ref):
		args = '[ options:dict ] label:idref'

		def digest(self, tex):
			super(ntislide.ntislidevideoref, self).digest(tex)
			self.starttime = _timeconvert( self.attributes['options']['start'] )
			self.endtime = _timeconvert(self.attributes['options']['end'])
			self.parentNode.slidevideo = self

	class ntislidetext(_LocalContentMixin, Environment):
		pass

def ProcessOptions( options, document ):

        document.context.newcounter( 'ntislidedeck' )
        document.context.newcounter( 'ntislide' )
        document.context.newcounter( 'ntislidevideo' )
