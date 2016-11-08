Whiteboard API v1
=================

This document contains the API for integrating the whiteboard into an application.  There are 2
whiteboards, one for IOS (iPad specifically) and one for use in web applications.  Both whiteboards
use the same object models, which are NTIUserData objects that can be saved and retrieved by the
dataserver.


Model
-----

  - CanvasShape:
  	An object that all other "shape" objects inherit from. All shapes are of unit size,
	positioned at the origin. The final location and size is determined
	by applying a transformation.

  	- Class - the class name, same as the shape
  	- transform - The 2d Affine transform to get final location, size, shape, and rotation.

  - CanvasPolygonShape
  	For lines, triangles, squares, etc. Adds the 'sides' value.

  - CanvasCircleShape
	For circles and ovals.

  - CanvasTextShape:
	An object that describes a (simple, plain) text box. Intended for labels.

  - CanvasUrlShape:
	An object that contains the URL of an image. For now, this URL
	must be a ``data`` URL.

  - CanvasPathShape:
	For freehand drawing. Adds an array of 'points' forming the path and
	a 'closed' flag to specify whether the path is open or closed.

  - Canvas:
  	This object is a container for a bunch of shapes, a scene, that can be saved.

	- shapeList - a list of WBShape objects.

Comments on Stroke and Fill
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Assumptions are:

- The CoreGraphics/Quartz rendering model, plus OmniQuartz extensions
  on the iPad

- An SVG-like rendering model on the browser.

They are pretty similar. The SVG model typically allows for a lot more
flexibility in units and representations than does tho iPad, but most
of them are convertible, so this is mainly an exercise in choosing the
set that's easiest to convert. (OTOH, there are some things the iPad
is more flexible with).

I think we can ignore joints and miters and dashes and fill rules and
such for now, so we'll limit ourselves to basic stroke and fill
properties. The four properties to be added to CanvasShape are:

strokeColor/fillColor: String specifying an sRGB color: "rgb( 0, 12, 123 )".

- This is directly acceptable to SVG.

- On the iPad, we'll need to chop off everything outside the
  parenthesis, remove the commas, then use
  `+[OQColor colorWithRGBAString]`.

- On the iPad, we have a -[OQColor cssString] to get output--it
  unconditionally includes the alpha component though ("rgba(
  r,g,b,a)"); more on that in a moment.

strokeWidth: String specifying a width in relative percentage points, scaled for the viewport (the same scale we use elsewhere): "22.0%".

- Directly acceptable to SVG.
- Easily parsed as a number on the iPad.
- Internally, you will probably scale this as as number between 0 and 1. The dataserver will
  only guarantee three digits of precision.
- Negative values are not acceptable. Values larger than 100% are not acceptable.

- The server will take either with or without trailing '%'. Will
  always produce trailing '%'.

strokeOpacity/fillOpacity: String giving a float between 0.0 and 1.0 for the opacity.

- Directly acceptable to SVG.

- On the iPad, can be parsed as a number, added to -1.0 to get the
  alpha. (alpha and opacity are inverse). Then `-[OQColor
  colorWithAlphaComponent:]` can be used to get the actual stroke/fill
  color.

On the iPad, we can use just one property to represent color and
alpha, an RGBA color. Rather than write the conversion code on the end
platforms, the server will add the following pseudo-properties:

strokeRGBAColor/fillRGBAColor: The combination of color and opacity (converted to alpha), directly parseable: "1.2 2.3, 3.4. 0.3".

- If this is set, the split properties are derived from it. If the
  others are set, they are combined to create this. If both are sent
  in, these take priority. Therefore, these should result in a set of
  properties that are directly usable on both platforms.

- On the iPad, can directly be read and produced with OQColor.

.. code-block:: cpp

	struct WBObject : Object {
	}

	struct CanvasAffineTransform { //Notice: This is NOT an Object.
		float a, b, c, d, tx, ty;
	}

	struct CanvasShape : WBObject {
		CanvasAffineTransform transform;
		string strokeColor, fillColor;
		string strokeWidth;
		string strokeRGBAColor, fillRGBAColor;
		float strokeOpacity, fillOpacity;
	}

	struct CanvasPolygonShape : CanvasShape {
		int sides;
	}

	struct CanvasCircleShape : CanvasShape {}

	struct CanvasTextShape : CanvasShape {
		string text; //Plain
	}

	struct CanvasPathShape: CanvasShape {
		// Points are represented as in SVG, with alternating
		// x, y coordinate values in a single array. Thus, this
		// array will always be an even number in length.
		float [] points;
		bool closed;
	}

	struct CanvasUrlShape: CanvasShape {
		string url;
	}

	struct Canvas : WBObject {
		CanvasShape[] shapeList;
	}

Model Scaling
-------------

All models are in standard coordinate system, which means the are represented by float values between
0 and 1.  All lengths are also scaled to this system.  This way the model or the list of models,
the canvas, can be scaled up to a rectangle of any size, by multiplying the x and y coordinates by the
standard x and y in the models.


iOS 5.0 (Required for ARC)
--------------------------

The NTIWhiteboardTouch framework is available to incorporate this into
an iOS application. There are 2 classes that will be used
specifically, they are detailed below.

`NTIWBToolBarViewController`

This is the view controller for the toolbar. Currently, the view comes
with all possible operations embedded. Create the view controller and
be sure to set it's delegate to handle tool presses. The
NTIWBCanvasViewController can and should be a delegate unless you need
to intercept calls before passing them to the canvas.

Create one using the initWithDelegate method and specify the size of
the toolbar view. Here's an example, note the delegate is a
NTIWBCanvasViewController class.

::

    self.toolbarViewController = [[NTIWBToolBarViewController alloc] initWithDelegate: self.canvasViewController
                                                                              andSize: CGRectMake(0, 0, 640, 60)];


`NTIWBCanvasViewController`

This is the view controller for the canvas space which has a scene
drawn upon it. If you have specified this as a delegate to your
toolbar view controller, then there shouldn't be any more work
necessary to start drawing on it.

Here's an example of how to create one, be sure to pass in the size of the canvas you want.

::

    self.canvasViewController = [[NTIWBCanvasViewController alloc] initWithSize: CGRectMake(0, 0, 640, 480)];


There are some properties that can be used to get data from the view controller:

    - canvas
	  gets the NTIWBCanvas object which can be imported or exported.  You can also set the scene by setting this property.

Web
---

  Currently being implemented.
