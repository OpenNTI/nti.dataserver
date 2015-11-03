===================
 Content Fragments
===================

.. automodule:: nti.contentfragments


Content Formats and Transformations
===================================

This package also defines some interfaces for content formats and
transformations between them, primarily among content stored and
manipulated as unicode text.

The root interfaces are content format and unicode content format.

.. autointerface:: nti.contentfragments.interfaces.IContentFragment
.. autointerface:: nti.contentfragments.interfaces.IUnicodeContentFragment
.. autoclass:: nti.contentfragments.interfaces.UnicodeContentFragment
	:members: __init__
	:show-inheritance:

A variety of interfaces and classes exist for specific types of
content. It is expected that there will be adapters registered for
converting among content types, most usually from plain text to some
other format. Note that these content formats represent fragments of

.. autointerface:: nti.contentfragments.interfaces.IPlainTextContentFragment
.. autoclass:: nti.contentfragments.interfaces.PlainTextContentFragment

Latex
-----

.. autointerface:: nti.contentfragments.interfaces.ILatexContentFragment
.. autoclass:: nti.contentfragments.interfaces.LatexContentFragment
.. automodule:: nti.contentfragments.latex

HTML
----

.. autointerface:: nti.contentfragments.interfaces.IHTMLContentFragment
.. autoclass:: nti.contentfragments.interfaces.HTMLContentFragment
.. automodule:: nti.contentfragments.html


Schema
======

.. automodule:: nti.contentfragments.schema
