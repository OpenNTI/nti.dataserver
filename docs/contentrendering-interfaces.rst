Content Rendering Interfaces
======================================

.. toctree::
	:maxdepth: 3

.. autointerface:: nti.contentrendering.interfaces.IEclipseMiniDomTopic
.. autointerface:: nti.contentrendering.interfaces.IIconFinder
.. autointerface:: nti.contentrendering.interfaces.IRenderedBookTransformer
.. autointerface:: nti.contentrendering.interfaces.IStaticVideoAdder
.. autointerface:: nti.contentrendering.interfaces.IEclipseMiniDomTOC
.. autointerface:: nti.contentrendering.interfaces.IRenderedBookValidator
.. autointerface:: nti.contentrendering.interfaces.IStaticRelatedItemsAdder
.. autointerface:: nti.contentrendering.interfaces.IStaticYouTubeEmbedVideoAdder
.. autointerface:: nti.contentrendering.interfaces.IVideoAdder
.. autointerface:: nti.contentrendering.interfaces.IBackgroundImageFinder
.. autointerface:: nti.contentrendering.interfaces.IDocumentTransformer
.. autointerface:: nti.contentrendering.interfaces.IRenderedBook

Content Formats and Transformations
-----------------------------------

This package also defines some interfaces for content formats and
transformations between them, primarily among content stored and
manipulated as unicode text.

The root interfaces are content format and unicode content format.

.. autointerface:: nti.contentrendering.interfaces.IContentFragment
.. autointerface:: nti.contentrendering.interfaces.IUnicodeContentFragment
.. autoclass:: nti.contentrendering.interfaces.UnicodeContentFragment
	:members: __init__
	:show-inheritance:

A variety of interfaces and classes exist for specific types of
content. It is expected that there will be adapters registered for
converting among content types, most usually from plain text to some
other format. Note that these content formats represent fragments of

.. autointerface:: nti.contentrendering.interfaces.ILatexContentFragment
.. autoclass:: nti.contentrendering.interfaces.LatexContentFragment
.. autointerface:: nti.contentrendering.interfaces.IHTMLContentFragment
.. autoclass:: nti.contentrendering.interfaces.HTMLContentFragment
.. autointerface:: nti.contentrendering.interfaces.IPlainTextContentFragment
.. autoclass:: nti.contentrendering.interfaces.PlainTextContentFragment
