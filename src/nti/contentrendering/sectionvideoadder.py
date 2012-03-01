#!/usr/bin/env python
import os

import logging
logger = logging.getLogger(__name__)

import urlparse

from . import interfaces
from zope import interface
from zope import component


def performTransforms(book, context=None):
	"""
	Runs all static video adders on the book.
	:return: A list of tuples (transformer,transformerresult)
	"""

	result = []
	utils = list(component.getUtilitiesFor(interfaces.IStaticVideoAdder,context=context))
	for name, util in utils:
		logger.info( "Running transform %s (%s)", name, util )
		result.append( (util, util.transform( book )) )

	return result


class AbstractVideoAdder(object):

	@classmethod
	def transform(cls,book):
		return cls(book)()

	def __init__( self, book ):
		self.book = book

	def __call__(self):
		pass

class YouTubeRelatedVideoAdder(AbstractVideoAdder):
	"""
	Reads from a file called nti-youtube-embedded-section-videos.txt and adds information
	the videos therein to the beginning of the section (additional videos go at the end).

	The file format consists of lines with fields separated by a space. (Lines beginning with a `#`
	are treated as comments.) The last field
	is the YouTube URL. The preceding fields name the page of content to which the URL is related.
	By default, this is a section number (CSS selector `dev.chapter.title .ref`), optionally preceded
	by 'Section', like so::

		[Section] X.Y http://youtube/...


	The leading field can also be an NTIID::

		tag:nextthought.com:2011-10:... http://youtube/...

	If the first field is the literal `*Selector*`, then the rest of the line (after the next whitespace)
	is taken as a CSS selector that will be evaluated to match the opening fields of the succeeding
	lines::

		*Section* .page-contents .worksheet-title
		Warm-Up 1 http://youtube/...


	"""
	interface.classProvides(interfaces.IStaticYouTubeEmbedVideoAdder)

	def __call__(self):
		"""
		:return: The number of videos added.
		"""
		youtube_file = os.path.join( self.book.contentLocation, '..', 'nti-youtube-embedded-section-videos.txt' )
		if not os.path.exists( youtube_file ):
			logger.info( "No youtube items at %s", youtube_file )
			return 0

		logger.info( "Adding videos at %s", youtube_file )
		# There can be many videos for a section.
		# We maintain a map from CSS selector to [(matching text, video url)] and
		# check each selector/matching text pair against each page
		# The first level can also be an NTIID to [(<ignored>, video url)]
		video_dbs = {}
		# The default
		video_db = []
		video_dbs['div.chapter.title .ref'] = video_db

		with open(youtube_file) as f:
			lines = f.readlines()
			for line in lines:
				line = line.strip()
				if not line or line.startswith( '#' ):
					# Comment, blank line
					continue
				parts = line.split()
				if len( parts ) < 2:
					logger.debug( "Ignoring invalid line %s in %s", line, youtube_file )
					continue
				if parts[0] == '*Section*':
					# A CSS selector is the remainder of the line. Whitespace may sorta matter
					# so we use the line as written
					selector = line[len('*Section*'):].lstrip()
					video_db = video_dbs.setdefault( selector, [] )
					continue

				# Validate the URL
				url_part = parts[-1]
				url_part = 'http://' + url_part if not url_part.startswith('http://') else url_part
				url_host = urlparse.urlparse( url_part ).netloc
				if url_host not in ('youtube.com', 'www.youtube.com'):
					logger.debug( "Ignoring unsupported URL host in %s in %s", line, youtube_file )
					continue

				if parts[0].startswith( 'tag:' ):
					append_to = video_dbs.setdefault( parts[0], [] )
				else:
					append_to = video_db

				to_match = None
				if parts[0] == 'Section':
					# Legacy behaviour for exact match of section numbers
					to_match = parts[1]
				else:
					# Match everything before the url
					to_match = line.rsplit( ' ', 1 )[0]
				append_to.append( ( to_match, url_part ) )

		def add_videos_to_topic( topic ):
			result = 0

			dom = topic.dom
			if dom:
				for k, v in video_dbs.items():
					matches = ()
					if k.startswith( 'tag:' ):
						if k == topic.ntiid:
							matches = [x[1] for x in v]
					else:
						text = dom( k ).text()
						# If missing, we get None
						if text:
							matches = [x[1] for x in v if x[0] == text]

					# If we have additions to make, we want to do so
					# at the first paragraph, if possible, and then at the end
					page_adder = dom( 'div.page-contents' ).append
					first_adder = dom('p:first').append if dom('p:first') else page_adder
					adders = (first_adder,page_adder)
					for vurl in matches:
						adder = adders[min(result,1)]
						result += 1
						adder( '<div class="externalvideo"><iframe src="%s" width="640" height="360" frameborder="0" allowfullscreen /></div>' % vurl )

				if result:
					topic.write_dom()
			# recurse
			for t in topic.childTopics:
				result += add_videos_to_topic( t )
			return result

		return add_videos_to_topic( self.book.toc.root_topic )
