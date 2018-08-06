#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces used during bulk email processing.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ValidTextLine as TextLine


class PreflightError(Exception):
    """
    Raised when an email process cannot be created.
    """


class IBulkEmailProcessMetadata(interface.Interface):
    """
    Information about the state of an email process.
    """

    startTime = Number(title=u"When the process last started",
                       description=u"Timestamp of when the process last started;"
                       u" 0 if there is no record",
                       default=0)

    endTime = Number(title=u"When the process last completed",
                     description=u"0 if the process has never run or is in progress",
                     default=0)

    status = TextLine(title=u"Human readable description of the process state")

    def save():
        """
        For the benefit of non-ZODB based process metadata, anytime this
        object is mutated this should be called to ensure that changes
        persist. (An implementation could use ``__setattr__`` to do this
        automatically, but this permits optimization by batching persistence
        calls.)
        """


class IBulkEmailProcessLoop(interface.Interface):
    """
    Something that implements the processing algorithem
    defined in this package. The process loop object itself should
    generally not be stateful, storing its mutable state information
    somewhere else; this is because it is instantiated or looked up
    many times.

    For now, the only supported way to provide an implementation of this
    interface is to subclass the provided value; this will become more pluggable.

    Implementations should be registered as named adapters
    from the request; their name is the name of the subpath used to get to them.
    (NOTE: This could/should be much more flexible using traversal.)
    """

    metadata = Object(IBulkEmailProcessMetadata)

    def initialize():
        """
        Prep the process for starting. Preflight it, then collect all the
        recipients and template arguments needed.

        :raises PreflightError: If for some reason the process definition is invalid.
        """

    def process_loop():
        """
        Process all the outstanding recipients. Called after
        :meth:`initialize`, possibly in a separate transaction or even
        in a separate operating system process.


        Typically this will be run in its own thread or greenlet (and thus outside
        the scope of a transaction and site manager). It generally
        should not raise exceptions.
        """

    def reset_process():
        """
        Reset the process back to initial conditions. If some instance of
        :meth:`process_loop` is running somewhere, this should cause it to
        cease running. For the process to work again, another call to :meth:`initialize`
        will be needed.
        """


class IBulkEmailProcessDelegate(interface.Interface):
    """
    Something that can fill in the details needed to successfully define
    a email process.

    These will typically be registered as named adapters from a context
    object and the request.
    """

    template_name = TextLine(title=u"A template asset spec")

    text_template_extension = TextLine(title=u"The extension for text templates",
                                       default=u".txt")

    def collect_recipients():
        """
        Return a sequence of recipients, possibly a generator.

        Each returned value is a :class:`dict` containing pickle-able
        values. Must have one key, ``email`` containing the email
        address (ideally a picklable that can be adapted to
        ``IEmailAddressable`` and ``IPrincipal``). May optionally have
        a key ``template_args`` which itself is a pickle-able
        dictionary; this argument will be passed to the method
        :meth:`compute_template_args_for_recipient`
        """

    def compute_sender_for_recipient(recipient):
        """
        Given a recipient dictionary previously produced by
        :meth:`collect_recipients`, return an address to be used
        as the sender, which should be the place to which bounce
        or complaint notifications are delivered. In the case of
        Amazon SES, this is a parameter to the ``SendRawEmail``
        API. Typically it will include VERP information.
        """

    def compute_fromaddr_for_recipient(recipient):
        """
        Given a recipient dictionary previously produced by
        :meth:`collect_recipients`, return an address to be used
        as the (user-visible) ``From`` value. This may
        or may not include VERP information.
        """

    def compute_template_args_for_recipient(recipient):
        """
        Given a recipient dictionary previously produced by
        :meth:`collect_recipients`, return the arguments that will be
        passed to the template for rendering.

        If this returns ``None``, then no template will be processed
        and *no email will be sent*.
        """

    def compute_subject_for_recipient(recipient):
        """
        Given a recipient dictionary previously produced by
        :meth:`collect_recipients`, return the subject line
        to use.
        """
