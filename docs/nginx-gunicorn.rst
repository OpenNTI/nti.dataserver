=================================
 nginx, gunicorn haproxy, and stunnel Setup
=================================

The combination of the nginx HTTP server, gunicorn WSGI server, and
pound reverse proxy is a popular one in the Python world. `nginx
<http://nginx.org/>`_ is a very lightweight HTTP server (relative to
Apache) and will be used for serving the static parts of the site.
`gunicorn <http://gunicorn.org/>`_ is a load balancer/monitor specifically
tailored to Python WSGI applications, especially those that use
gevent. `HAProxy <http://haproxy.1wt.eu>`_ is the reverse proxy
that sits in front of both of these and mediates between them (it can
also handle load balancing);
(it would not be necessary if nginx could handle WebSockets, but as of
1.1.12, it cannot). Finally, `stunnel <http://www.stunnel.org/>`_
serves as the SSL termination point, and forwards all actual serving
to HAProxy (stunnel is needed because it supports arbitrary TCP
connections and arbitrary duration; neither amazon's load balancing
service nor the open-source Poind support WebSockets).

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

As of this writing, the latest nginx stable version is 1.0.12. On linux,
follow `the instructions <http://wiki.nginx.org/Install>`_ to install
nginx (on Amazon linux, don't forget to add a ``priority=1`` line to the
Yum configuration). On OS X, use MacPorts. If the version that comes
with macports is too old, create a custom portfile for 1.0.12 and follow
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
and start the dataserver (e.g, ``pserve config/development.ini``) you should be able to
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

It is very easy to use gunicorn with the above setup. The gunicorn
server is the default server in ``config/development.ini`` so the
``pserve`` command by default will launch gunicorn. (This is a rather
specific configuration; see gunicorn.py for more info.)

In the future, we may be able to bind to a unix
domain socket (a file) instead of a port; this might be a bit faster.

::

	openssl req -x509 -newkey rsa:1024 -keyout srv_comb.pem -out srv_comb.pem -days 365 -nodes

HAProxy
=======

The 1.5-dev series of haproxy is required for proper proxy support.
Version 1.5-dev7 is current. On linux, compile with:

::

	make TARGET=linux26 PREFIX=/opt/nti

If you first install the haproxy RPM, then you can patch
``/etc/init.d/haproxy`` to use the new binary. The configuration would
reside in ``/etc/haproxy/haproxy.cfg``:

::

  global
    log         127.0.0.1 local2
    maxconn     4096 # Total Max Connections. This is dependent on ulimit
    nbproc      1

  defaults
    mode        http
	# If we don't set this, then we lose X-Forwarded-For
	option http-server-close

  frontend all 0.0.0.0:80
	option httplog
	log global
    timeout client 86400000
	# Listen on the socket for incoming SSL in proxy mode
	# We give it a specific id so that we can match in an ACL
	# (We can't match on ssl itself because that's already been handled)
    bind /var/run/ssl-frontend.sock user root mode 600 id 42 accept-proxy
    default_backend www_backend

	acl is_websocket hdr(Upgrade) -i WebSocket
	acl is_websocket hdr_beg(Host) -i ws

	acl is_dyn path_beg /dataserver
	acl is_dyn path_beg /library
	acl is_dyn path_beg /socket.io
	# Consider a path_sub here for Search urls

	acl is_ssl so_id 42

	# Block some common attack vectors
	acl is_blocked_name path_end .php .asp .jsp .exe .aspx
	block if is_blocked_name

    use_backend socket_backend if is_websocket
    use_backend socket_backend if is_dyn

	# Let gunicorn/nginx know if we are dealing with an incoming HTTPS request
	# (This is a default 'secure-header' in gunicorns conf)
	reqidel ^X-FORWARDED-PROTOCOL:.*
	reqadd X-FORWARDED-PROTOCOL:\ ssl if is_ssl

	# Go to the app by default
	redirect location /NextThoughtWebApp/index.html code 301 if { path / }



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

These instructions are for version 4.52; any version greater than 4.44
is required in order to add proxy support so that HAProxy knows the
originating IP and can pass it on to nginx.

On AWS, first install the available stunnel distribution. Then
download and compile the latest stunnel like so:

::

	./configure --prefix=/opt/nti --disable-dependency-tracking --with-threads=pthread; make

::

	cert = /opt/nti/ssl_certs/srv_comb.pem

	[https]
	accept = 443
	connect = /var/run/ssl-frontend.sock
	protocol = proxy

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
