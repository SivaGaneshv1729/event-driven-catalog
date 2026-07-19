#!/bin/bash

# Apply database migrations
python manage.py makemigrations
python manage.py migrate

# Start consumer worker in the background
python manage.py consume_events &

# Start the web server in the foreground
python manage.py runserver 0.0.0.0:8001
