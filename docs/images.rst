=====================
 Working with images
=====================

This document describes some special support functions the server
provides for the browser.

data URLs
=========

For the purpose of uploading avatars images in legacy browsers, the
server offers two urls to accept a POST uploaded image an respond
with a ``data:`` URL string.

.. autofunction:: nti.appserver.zope_file_views.image_to_dataurl

.. autofunction:: nti.appserver.zope_file_views.image_to_dataurl_extjs

Echoing Images
==============

A function for echoing the data of images is provided by this view:

.. autofunction:: nti.appserver._hacks.echo_image_url

This is useful in extremely limited circumstances, as motivated by the
following conversation.

On Nov 16, 2012, at 17:28, Christopher Utz <chris.utz@nextthought.com> wrote::

>> Jason,
>> I don't know if you recall any of the discussion that took place
>> around the new image annotation feature. The feature was tracked by
>> card
>> https://trello.com/card/image-annotations/505fb1d401f88fde62008f74/319
>> Unfortunately there is not a ton of info about how it works in that
>> card. I'll try and summarize, but Jonathan feel free to correct me
>> where I misspeak. It basically amounts to creating a note that
>> contains a whiteboard, which is initialized with a canvas url shape
>> for the content image that was clicked on. Right now as implement
>> this means taking the img source url from the content and creating
>> a canvas URL shape using that URL. All other things ignored this
>> implementation seems like it would have the undesired behavior that
>> if the data behind a content url ever changes all the whiteboards
>> change as well. Not saying this would ever happen since I think we
>> control all the content images at this point, but I am imaging the
>> case you hear about often where someone knowingly or unknowingly
>> links to someone else's image, the owner finds out, and then all of
>> a sudden you have some inappropriate pictures showing up on your
>> website.
>>
>> Even given all that, it seemed to work ok until we put it out in
>> prod where the content is hosted from a different domain.
>> Apparently once you add an image from an outside domain to a
>> canvas, you can no longer "get the bytes" of the canvas to generate
>> something like a png thumbnail. That means the webapp can't
>> generate the thumbnail that gets shown in various places in the
>> app. In the past it sounds we have tried a number of things client
>> side to get around similar issues, but we never had any luck. If
>> you have any bright ideas we are open to suggestions. The one thing
>> we came up with was another dataserver endpoint similar to what you
>> implemented for the avatar upload. The app could send the
>> dataserver the url of the image and the dataserver would consume
>> the endpoint and echo back a dataurl. This would handle the copy to
>> avoid the situation described above, but more importantly it would
>> get the image data into the proper domain so that we don't have any
>> canvas restrictions like we are seeing now.

On Nov 16, 2012, at 6:16 PM, Jason Madden wrote::

> The good news is that images support CORS, and now (as of last
> month) S3/CloudFront do as well. So with a fairly simple code change
> and some tweaks to the uploaded content, the problems go away. See
> https://developer.mozilla.org/en-US/docs/CORS_Enabled_Image and
> http://aws.typepad.com/aws/2012/08/amazon-s3-cross-origin-resource-sharing.html
>
> The bad news, as usual, is that IE9 doesn't support CORS at all, let
> alone for images, so that means we have to do something different
> for it. Turning arbitrary images into data: URLs is probably not a
> tractable solution; they'd be far too large, and there are limits
> (they only worked acceptably in the original CanvasURLShape when the
> clients pre-shrunk the images to be low-res.) Instead, we could do
> something like we once did for YouTube videos, and "proxy" image
> URLs through the dataserver:
>
> - the browser detects a cross-origin image, and that it is on IE9
>
> - the browser rewrites the image url to be something like
>   '//dataserver2/@@echo_image_url?image_url=http://location/of/image.png'
>
> - The DS gets the request, reads the query, fetches the image from
>   the given URL, and echos back the original byte data and
>   Content-Type to the browser
>
> That has a number of problems (e.g., it introduces an extra hop,
> bypasses the CDN, occupies dataserver resources, and is generally
> slow-as-molasses) so it would be crucial to only do it in the IE9
> case, not the usual case.
