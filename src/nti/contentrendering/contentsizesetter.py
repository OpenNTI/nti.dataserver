#!/usr/bin/env python2.7

import logging
logger = logging.getLogger(__name__)

contentSizeName = 'NTIRelativeScrollHeight'

def transform(book,context=None):
	"""
	Use the toc file to find all the pages in the contentLocation.
	Use phantomjs and js to render the page and extract the content size.
	Stuff the contentsize in the page as a meta tag and add it to toc
	:param context: A zope `IComponentLookup`. Currently unused.
	"""

	eclipseTOC = book.toc
	_storeContentSizes( book.toc.root_topic )

	eclipseTOC.save()

def _storeContentSizes(topic):
	"""
	:param topic: An `IEclipseMiniDomTopic`.
	"""

	contentHeight = topic.get_scroll_height()
	if contentHeight <= 0:
		# Some of these are expected because we don't
		# get the page info for all the pages (like the index)
		# for some reason
		logger.warn( "Failed to get content size for %s", topic )
		return

	topic.set_content_height( contentHeight )

	for child in topic.childTopics:
		_storeContentSizes( child )
