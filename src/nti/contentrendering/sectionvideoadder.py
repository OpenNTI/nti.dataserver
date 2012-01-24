#!/usr/bin/env python
import os

import logging
logger = logging.getLogger(__name__)

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

	The file format consists of lines with fields separated by a space. The last field
	is the YouTube URL. The preceding fields is a section number, optionally preceeded
	by 'Section', like so::

		[Section] X.Y http://youtube/...


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
		# There can be many videos for a section; we simply
		# keep a list of tuples and search through it for each page.

		video_db = []
		with open(youtube_file) as f:
			lines = f.readlines()
			for line in lines:
				parts = line.split()
				if parts[0] == 'Section':
					parts = parts[1:]
				video_db.append( tuple(parts) )

		def add_videos_to_topic( topic ):
			result = 0
			sec_num = None
			dom = topic.dom
			if dom:
				sec_num = dom("div.chapter.title .ref").text()
				# If missing, we get None
			if sec_num:
				# Find the applicable videos
				for vsec, vurl in video_db:
					if vsec == sec_num:

						adder = dom('p:first').append if result == 0 else dom('div.page-contents').append
						result += 1
						adder( '<div class="externalvideo"><iframe src="%s" width="640" height="360" frameborder="0" allowfullscreen /></div>' % vurl )
				if result:
					topic.write_dom()
			# recurse
			for t in topic.childTopics:
				result += add_videos_to_topic( t )
			return result

		return add_videos_to_topic( self.book.toc.root_topic )
