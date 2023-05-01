#!/bin/bash
gunicorn --timeout 90 -b 0.0.0.0:5000 'app:create_app()'
