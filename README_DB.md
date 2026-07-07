SQLite database setup
=====================

The app now stores each prediction in a local SQLite database file named crop_disease.db in the project root.

Database table:
- predictions
  - id
  - filename
  - result_json
  - created_at

The database file is created automatically when the Flask app starts.
