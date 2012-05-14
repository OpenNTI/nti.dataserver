===========================================
Serving Content from a CDN
===========================================

This document will outline some notes and observations on how we can
serve content from a high-capacity data store and CDN, specifically
Amazon S3 and Amazon CloudFront.

Background on Technologies
==========================

This section will provide some background on the Amazon technologies,
including their strengths and weaknesses that drive the necessary approach.

Amazon S3
---------

`Amazon S3 <http://aws.amazon.com/s3/>`_ (for *simple storage
service*) is a high-capacity, low-latency, high-availability object
store in which data is stored in named *buckets,* with each object in
a bucket having a developer-assigned unique identifier. Although S3
does not imitate a filesystem (contrast with EBS volumes), it does
have the capability of serving as an HTTP server, with a bucket being
mapped to a domain name and the identifiers being treated like URL
paths.

Price-wise, S3 is slightly more expensive than EBS volumes for raw
storage in the base tier ($0.125/GB vs $0.100/GB). However, (1) the
*reduced redundancy storage* is slightly cheaper at $0.093/GB and
\(2) S3 is tiered, with higher tiers being less expensive. In EBS,
you pay for IO requests, in S3 you pay for HTTP requests. It probably
comes out about the same.

An account is limited to 100 buckets, which should have names that are
valid DNS names.

Amazon CloudFront
-----------------

`Amazon CloudFront <http://aws.amazon.com/cloudfront/>`_ is a
distributed Content Distribution Network (CDN). In contrast to some
CDN approaches, CloudFront is takes a dynamic, caching approach: no
content is every specifically pushed to CloudFront. Instead, when
content is requested from CloudFront, if it is not already available
and valid in CloudFront, it is cached by making a request to the
*origin server.* Explicit invalidations of cached content is
possible, but expensive; versioned URLs are preferred.

Recently, CloudFront has been upgraded to `handle query strings <http://aws.typepad.com/aws/2012/05/amazon-cloudfront-support-for-dynamic-content.html>`_,
allowing for some measure of dynamic content. However, it does not
handle HTTP cookies, nor does it support any HTTP methods other than
GET and HEAD. While it does support some HTTP-based streaming
protocols for media, it does not support WebSocket requests.

CloudFront can use any origin server, but is particularly well suited
to distributing resources stored in S3 or computed on an EC2 node.
CloudFront is priced separately from S3 or EC2 at $0.120/GB
transferred plus the usual (and confusingly hard to calculate) price
per requests (in this case $0.0075/10,000 HTTP requests or
$0.0100/10,000 HTTPS requests).

CloudFront is configured by setting up *distributions,* which is
essentially a mapping of URL patterns to origin servers. An account is
limited to 100 distributions.

Using S3/CloudFront
===================

This section will talk about how S3 and CloudFront can be leveraged.

CNAMEs
------

One way in which S3 and CloudFront are used is as a CNAME (DNS
*canonical name*). This effectively creates an alias for a given
domain name and passes all traffic through CloudFront or S3. For
completely static content, or content that is only ever read (even if
dynamically generated) this works well. However, for content that is
written, this is not possible as CloudFront does not support write
requests.

While it would be possible for the dataserver to proxy requests for S3
stored data, that would tend to defeat the point of having static
content in S3 to start with, as all traffic would be forced through
the dataserver front end, which would inevitably be slower than a
native S3 request (plus adding extra data transfer charges). For
CloudFront, it would completely negate the benefit of the edge caching.

Thus, to effectively store and serve static content from
S3/CloudFront, an application will be talking to (a minimum of) two
domains: one for reading/writing to the dataserver and WebSockets, and
one for reading the static content. Many of the pieces for this are in
place now, as the applications do not make assumptions about the
layout of the static content's URL space, instead letting the
dataserver redirect them through the /NTIIDs URL. There are two pieces
missing, however.

Cross Origin Requests
---------------------

First and most seriously is the issue of cross-origin requests. This
is only an issue for the browser, and arises because of the multiple
domains involved. We've generally held that we could either (a) proxy
all requests through a single domain (to avoid any cross-origin
requests) or (b) rely on CORS headers (to bypass cross-origin
restrictions). As we saw earlier, option (a) is ruled out as
inefficient or pointless. Option (b) is only a possibility if the
browser source is served from the S3/CloudFront domain and the
dataserver is a separate domain because the S3/CloudFront HTTP servers
*do not support CORS headers* (in fact, they are very restricted in
what HTTP headers they support). Therefore, we would be relying on the
dataserver to supply CORS headers and the browser to respect them.

For example:

===================  ==============================
Content              Location
===================  ==============================
Browser Source Code  static.nextthought.com
All Content          static.nextthought.com
Dataserver           dynamic.nextthought.com + CORS
===================  ==============================

This has the advantage of working with no changes to either application,
and no changes to the content.

We've had some trouble with certain browsers getting CORS to work. If
that becomes a showstopper, there is a fallback position using JSONP
(even the IFrame currently being used for the browser reader falls
into the same-origin restriction if we need to manipulate it, and we
do, so some cross-origin workaround is a necessity). In this layout,
the positions of static content and dynamic content are reversed, with
the static content being wrapped in JSONP wrappers before being
uploaded to S3/CloudFront. This requires extra work on the content
creation side of things, and may require extra data storage (one JSONP
wrapped version for the browser, one plain version for the pad). It
requires some (fairly minimal?) extra work on the browser to enable
the JSONP callbacks. I think images and other resources Just Work,
once the browser can make the XHR request to get the primary data.

This layout looks like:

===================  ==============================
Content              Location
===================  ==============================
All Content          static.nextthought.com + JSONP
Browser Source Code  dynamic.nextthought.com
Dataserver           dynamic.nextthought.com
===================  ==============================

Kindle Cloud Reader
+++++++++++++++++++

For what its worth, this is the approach that Kindle Cloud Reader
takes. Each book is broken into fragments which are GZIPped and
base-64'd and placed into a JSONP wrapper. These fragments are placed
into S3, and CloudFront is put in front of S3. The browser application
is served from ``read.amazon.com`` and makes XHR requests to a
``cloudfront.net`` domain to fetch the fragments. Doubtlessly the
fragments are self-expiring S3 items.

Resources and Naming
--------------------

The second piece of the puzzle is managing the resources related to
each rendered unit of content. Because we are limited to 100 buckets,
we cannot simply throw each rendered unit of content into its own
bucket. We have to expect that many units of content will share the
same bucket.

Consequently, "file" names have to be unique. For generated resources,
we are already hashing names and can safely share buckets, assuming
the hashes are correct and unique to the data they are hashing (I
think they are for TeX sources, I'm sure they *are not* for image
sources). What remains is to do something about HTML file names plus
the various other bits that are duplicated between projects
(eclipse-toc.xml, archive.zip). Finally, if we are sharing resource
data, we need some way to do "garbage collection" of resources that
are no longer referenced.

.. note:: While we could probably use some sort of "directory-like"
	identifier for objects in the bucket, much as we lay things out on
	the filesystem now, that seems to lose a lot of opportunity for
	sharing, particularly of resources. Even if the resources shared
	cross-content are few, when we version URLs for CloudFront, the
	resources shared from one content version to the next are likely
	to be very many.
