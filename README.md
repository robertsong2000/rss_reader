# RSS Reader Web Application

A simple web-based RSS reader built with Flask that allows you to add RSS feeds, automatically update them, and read articles in a clean interface.

## Features

- **Feed Management**: Add, remove, and list RSS feeds
- **Automatic Updates**: Feeds are automatically refreshed every 30 minutes
- **Article Reading**: Read articles from your feeds with a clean interface
- **Mark as Read**: Track which articles you've read
- **Filtering**: Filter articles by feed or read/unread status
- **Responsive Design**: Works on desktop and mobile devices

## Installation

1. Clone or download the project files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the RSS reader:

```bash
python app.py
```

By default, the application runs on port 5001. You can specify a different port:

```bash
python app.py --port 8080
```

Other options:
```bash
python app.py --host 127.0.0.1 --port 3000 --debug
```

Open your browser and navigate to `http://localhost:5001` (or your specified port).

## API Endpoints

### Feeds
- `GET /feeds` - List all feeds
- `POST /feeds` - Add new RSS feed
- `DELETE /feeds/<id>` - Remove feed
- `POST /feeds/<id>/refresh` - Manually refresh feed

### Articles
- `GET /articles` - List articles (with optional filtering)
- `POST /articles/<id>/read` - Mark article as read

## Database

The application uses SQLite for data storage. Two tables are created:
- `feeds`: Stores feed information
- `articles`: Stores article data

The database file `rss_reader.db` will be created automatically when you first run the application.

## Dependencies

- Flask - Web framework
- feedparser - RSS feed parsing
- APScheduler - Background task scheduling
- Flask-CORS - Cross-origin resource sharing
- requests - HTTP library

## Project Structure

```
rss_reader/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── requirements.md     # Detailed requirements
├── templates/
│   └── index.html      # Main web interface
└── rss_reader.db       # SQLite database (created automatically)
```

## Configuration

You can modify the following in `app.py`:
- Update interval (currently 30 minutes)
- Database file name
- Default port and host settings

## License

This project is open source and available under the MIT License.