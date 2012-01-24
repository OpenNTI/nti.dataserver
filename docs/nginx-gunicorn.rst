=================================
 nginx, gunicorn and pound Setup
=================================

The combination of the nginx HTTP server, gunicorn WSGI server, and
pound reverse proxy is a popular one in the Python world. `nginx
<http://nginx.org/>`_ is a very lightweight HTTP server (relative to
Apache) and will be used for serving the static parts of the site.
`gunicorn <http://gunicorn.org/>`_ is a load balancer/monitor specifically
tailored to Python WSGI applications, especially those that use
gevent. `Pound <http://www.apsis.ch/pound/>`_ is the reverse proxy
that sits in front of both of these and mediates between them (it can
also handle load balancing); it serves as the SSL termination point
(it would not be necessary if nginx could handle WebSockets, but as of
1.1.12, it cannot).

These are basic setup instructions for OS X and Amazon Linux. The Linux
instructions are derived from `a blog
post <http://adrian.org.ar/python/django-nginx-green-unicorn-in-an-ubuntu-11-10-ec2-instance>`_.

nginx Setup
===========

Our end goal will be to get nginx serving static content from
``/Library/WebServer/Documents/`` on port 8080 (Linux) or port 8080 (OS X)
with gzip compression enabled. Dynamic content requests will be
forwarded to port 8081. On Linux, we additionally setup Pound to serve
on port 80 and switch between nginx and gunicorn in order to handle
WebSockets and SSL. (The section `SSL And Complete Configuration`_
gives the final configuration.)

Installation
------------

As of this writing, the latest nginx stable version is 1.0.11. On linux,
follow `the instructions <http://wiki.nginx.org/Install>`_ to install
nginx (on Amazon linux, don't forget to add a ``priority=1`` line to the
Yum configuration). On OS X, use MacPorts. If the version that comes
with macports is too old, create a custom portfile for 1.0.11 and follow
the normal procedure.

Mac OS X
~~~~~~~~

Begin by copying ``/opt/local/etc/nginx/nginx.conf.default`` to
``/opt/local/etc/nginx/nginx.conf.`` Edit this new file to enable the
commented-out logging (make sure the paths point to
``/opt/local/var/log/nginx/``), gzip (also add a ``gzip_types`` line to
allow compression of more than ``text/html``:
``gzip_types application/x-javascript application/javascript text/xml;``)
and keepalive (add ``keepalive_disable none;``). In the ``server``
stanza, point the root to ``/Library/WebServer/Documents/`` and listen
on port 8080; deny access to .htaccess files.

Test that this has worked by browsing
``http://localhost:8080/prealgebra/``. Use the web inspector to verify
that resources were gzipped.

Note that gzip requires a fixed list of types and cannot accept
wildcards. These instructions set up gzip for static content types only,
not the myriad of content types used by the OData implementation of
dataserver2.

Linux
~~~~~

On Linux, the main configuration file is ``/etc/nginx/nginx.conf``;
enable gzip in this file. This file includes ``conf.d/*.conf``; proceed
to make the rest of the changes in ``conf.d/default.conf``, leaving the
port at 80.

The ``/Library/WebServer/Documents/`` tree should be owned by the
``nginx`` user.

Proxy Configuration
-------------------

The nginx process will redirect requests to the gunicorn (or standalone)
dataserver by proxy. There are two methods to accomplish this, explicit
and implicit. Implicit will probably be preferred.

With either method, after you make the changes and restart nginx (e.g.,
with ``nginx -s reload`` on OS X or ``service nginx reload`` on Linux)
and start the dataserver (e.g, ``python app.py``) you should be able to
use a single port (80 or 8080) to request both static content, hit the
dataserver, and search within a unit of content.

Note that neither method supports websockets, so socket.io will fallover
to using XHR-polling. This is due to nginx not supporting 'Connection:
Upgrade' from the proxy (no matter how hard you fight). In the future,
we will consider using the tcp proxy for this (it requires different
ports for websockets and the main app, sadly).

Explicit Proxy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this method, we explicitly list the paths that we want proxied. To do
this, add a ``location`` configuration to the ``server`` section of the
nginx configuration:

::

    location ~ /dataserver[2]?|/.*/Search/|/socket.io/ {
        proxy_buffering off;
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_connect_timeout 10;
        proxy_read_timeout 10;
        proxy_pass http://localhost:8081;
    }

Implicit Proxy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method functions much like Passenger: if the file exists on disk,
serve it. Otherwise, pass the request through to the dataserver. This
takes two blocks, one at the ``http`` level:

::

        upstream appserver {
                server localhost:8081 fail_timeout=10;
        }

And the second within the ``server`` level (this replaces the existing
``location /`` block:

::

    root   /Library/WebServer/Documents;
    location / {
        # checks for static file, if not found proxy to app
        try_files $uri @proxy_to_app;
        index  index.html index.htm;
        expires +30d;
    }

    location @proxy_to_app {
        proxy_buffering off;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        proxy_pass   http://appserver;
    }

SSL and Complete Configuration
------------------------------

If we are using nginx as the SSL termination point, we would stop
here. The nginx wiki has `good instructions
<http://wiki.nginx.org/HttpSslModule>`_ on how to enable SSL for
nginx. Once that's done, the entire configuration for the dataserver
should look something like this:


::

	sendfile        on;
	tcp_nopush     on;

	keepalive_timeout  65;
	keepalive_disable none;

	gzip  on;
	gzip_types application/xml application/x-javascript application/javascript text/xml application/vnd.nextthought.workspace+json;
	gzip_proxied any;
	upstream appserver {
		server localhost:8081 fail_timeout=10;
	}
	server {
		#listen       8080;
		server_name  alpha-ec2.nextthought.com;
		listen 443 default_server ssl;
		listen 80;
		ssl_certificate /opt/nti/ssl_certs/server.crt;
		ssl_certificate_key /opt/nti/ssl_certs/server.key;

		root   /Library/WebServer/Documents;

		location / {
			# checks for static file, if not found proxy to app
			try_files $uri @proxy_to_app;
			index  index.html index.htm;
			expires +30d;
		}

		location @proxy_to_app {
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header Host $http_host;
			proxy_buffering off;
			proxy_redirect off;

			proxy_pass   http://appserver;
		}

		# deny access to .htaccess files, if Apache's document root
		# concurs with nginx's one
		#
		location ~ /\.ht {
			deny  all;
		}

	}



gunicorn setup
==============

It is very easy to use gunicorn with the above setup. The command is
simple:

::

	gunicorn -k nti.appserver.gunicorn.GeventApplicationWorker nti.appserver.gunicorn:app -b 127.0.0.1:8081

This uses our application worker (the ``-k`` argument) based on gevent
and so should be very scalable while also using our AppServer and
handler infrastructure (this taking care of the two problems noted
below). Note that you cannot preload the application into the master
gunicorn process. In the future, we may be able to bind to a unix
domain socket (a file) instead of a port; this might be a bit faster.

Legacy gunicorn info
--------------------

At this time, there are two problems using gunicorn. First and most
importantly, the dataserver is tied to using the :py:class:`nti.appserver.application.AppServer`
WSGI server class. Not only does this class handle SocketIO sessions
and websockets, it also handles database transactions. Heavy
refactoring will be required to break this dependency (but this will
be worthwile for greater portability and hopefully less implicit
"magic").

Secondly, the gunicorn workers we would like to use, the gevent workers,
depend on having gevent monkey-patch the entire system; this is
incompatible with threads, especially as used by ZEO. This can be worked
around using the sync workers. However, if that's the case, then it's
not clear there's not a whole lot we get out of gunicorn that we
couldn't get out of nginx itself. A custom subclass of the gevent worker
might be used to solve this problem.

Pound
=====

Pound can be used to serve SSL and dispatch WebSocket traffic
securely. Version 2.5 is available from yum (Linux) and MacPorts (OS
X). A configuration that serves as the SSL termination and routes all
Socket.IO (and hence WebSocket) traffic to the dataserver, while
letting nginx handle everything else (potentially also going through
nginx; this step could be optimized to eliminate a hop) is below.

::

	ListenHTTP
    	Address 0.0.0.0
		Port 80
	End

	ListenHTTPS
		Address 0.0.0.0
	    Port    443
	    Cert    "/opt/nti/ssl_certs/srv_comb.pem"
	End

	# One service: the dataserver for socket.io
	Service
		URL "/socket.io/"
		BackEnd
			Address 127.0.0.1
			Port 8081
		End
	End

	# One service: nginx for static files
	Service
	    BackEnd
	        Address 127.0.0.1
	        Port    8080
	    End
	End

With this in place, the nginx configuration is modified to not listen
on port 80 or 443 and not use SSL; instead it listens on port 8080.
Pound requires a combined private key and certificate file instead of
two separate files like nginx; you can obtain this by concatenating
the two files previously referenced in the nginx configuration. Or you
can create one specifically for this purpose with the following
command:

::

	openssl req -x509 -newkey rsa:1024 -keyout srv_comb.pem -out srv_comb.pem -days 365 -nodes

HAProxy
=======

Version 1.4.18.

::

  global
    log         127.0.0.1 local2
    maxconn     4096 # Total Max Connections. This is dependent on ulimit
    nbproc      1

  defaults
    mode        http

  frontend all 0.0.0.0:80
	option httplog
	log global
    timeout client 86400000
    default_backend www_backend
    acl is_websocket hdr(Upgrade) -i WebSocket
    acl is_websocket hdr_beg(Host) -i ws

	acl is_dyn path_beg /dataserver
	acl is_dyn path_beg /library
	acl is_dyn path_beg /socket.io
	# Consider a path_sub here for Search urls

    use_backend socket_backend if is_websocket
    use_backend socket_backend if is_dyn

  backend www_backend
    balance roundrobin
    option forwardfor # This sets X-Forwarded-For
    timeout server 30000
    timeout connect 4000
    server nginx 127.0.0.1:8080 weight 1 maxconn 1024

  backend socket_backend
    balance roundrobin
    option forwardfor # This sets X-Forwarded-For
    timeout queue 5000
    timeout server 86400000
    timeout connect 86400000
    server dataserver 127.0.0.1:8081 weight 1 maxconn 1024

Stunnel
=======

::

	cert = /opt/nti/ssl_certs/srv_comb.pem

	[https]
	accept = 443
	connect = 80


Upstart
=======

The following is an upstart configuration to put in
``/etc/init/dataserver.conf`` for Amazon linux.

::

    description "Dataserver"
    start on runlevel [2345]
    stop on runlevel [06]

    respawn
    respawn limit 10 5

    # setuid seems not to be supported in this version
    #setuid ec2-user
    #exec /home/ec2-user/app_run.sh

    exec /bin/su - ec2-user /opt/nti/bin/gunicorn -k nti.appserver.gunicorn.GeventApplicationWorker nti.appserver.gunicorn:app -b 127.0.0.1:8081

