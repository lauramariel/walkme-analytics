# walkme-analytics

This is a Flask app for receiving webhooks from WalkMe. It listens on two endpoints that WalkMe sends data to which triggers every time there is either a started walkthrough or a completed onboarding task. WalkMe doesn't have detailed user info, so this app looks up the user email in Firestore and adds this to the payload, and then stores the updated payload in a MongoDB database. Currently it's deployed and managed using Docker Compose on a single server.
