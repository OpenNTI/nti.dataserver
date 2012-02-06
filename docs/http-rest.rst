Dataserver HTTP and REST Notes
==============================

MIME Types
----------

The dataserver makes heavy use of MIME types. In particular, the
result format when making requests from the dataserver is driven by
the HTTP ``Accept`` header, while the interpretation of data sent to
the dataserver is driven by the ``Content-Type`` header. The values
used here are also echoed in the datastructures sent from the
dataserver in the ``MimeType`` field (obsoleting the older ``Class`` field).

Our MIME types (and our use of ``Content-Type`` and ``Accept``) is
similar to `github's <http://developer.github.com/v3/mime/>`_. In
particular, our format is::

  application/vnd.nextthought[.version][.class][.param][+json|plist]

If ``version`` is missing, it means the latest. ``Class`` is required
for create and update operations (unless specified in the data itself;
the mime type overrides the data); it is ignored in the ``Accept``
header. (The ``class`` is the lowercased version of the old ``Class`` value from
the data.)

No versions are currently defined. No parameters are currently defined.
JSON is the default but may be specified with ``+json``.

Also valid in Accept headers are::

  application/json (for the default, latest JSON encoding)
  application/xml  (for the default, latest XML encoding in PList schema)

Therefore, ``application/json`` is equivalent to ``application/vnd.nextthought+json``
and ``application/xml`` is equivalent to application/vnd.nextthought+plist.
