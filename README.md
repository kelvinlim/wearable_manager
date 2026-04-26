# wearable manager

This project is to create a new wearable_manager web application that handles user registration and data subscriptions for fitbit and garmin wearables.  We will start with the fitbit using the new Google health api described here https://developers.google.com/health/migration

The goal is for the data for a registered user flow to this app via subscription/webhook.

I would plan for data for a user for a single day would all be in a single json payload.

Several linked folders of code are provided for reference.

fitbitreg - flask app for fitbit user registration using Oauth2

garmin_django - a django app that manages studies and users and data.  Some of the data structures may be useful.


The new app would use a different architecture.

Postgres database
Sqlalchemy 2.0 async
alembic for migrations

fastapi backend

react frontend

User authentication using google auth

