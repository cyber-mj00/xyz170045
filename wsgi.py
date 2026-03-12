#!/usr/bin/env python
import sys

sys.path.insert(0, '/home/dl.170045.xyz/xyz170045')

from xyz170045 import create_app

# Create the Flask application
app = create_app()

# Expose "application" for WSGI servers like uWSGI, Gunicorn, mod_wsgi
application = app

