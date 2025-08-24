from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import feedparser
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import os
import argparse
import json
import csv
import io

app = Flask(__name__)
CORS(app)

DATABASE = os.getenv('DATABASE_PATH', 'rss_reader.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            last_updated TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            content TEXT,
            published_date TEXT,
            read_status BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (feed_id) REFERENCES feeds (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def parse_feed(url):
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            return None
        
        return {
            'title': feed.feed.get('title', 'Untitled Feed'),
            'entries': [{'title': entry.get('title', 'Untitled'),
                        'link': entry.get('link', ''),
                        'content': entry.get('summary', ''),
                        'published': entry.get('published', '')} 
                       for entry in feed.entries]
        }
    except Exception as e:
        print(f"Error parsing feed {url}: {e}")
        return None

def update_feed(feed_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT url FROM feeds WHERE id = ?', (feed_id,))
    feed = cursor.fetchone()
    
    if feed:
        feed_data = parse_feed(feed['url'])
        if feed_data:
            for entry in feed_data['entries']:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO articles 
                        (feed_id, title, link, content, published_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (feed_id, entry['title'], entry['link'], 
                          entry['content'], entry['published']))
                except Exception as e:
                    print(f"Error inserting article: {e}")
            
            cursor.execute('''
                UPDATE feeds SET last_updated = ? WHERE id = ?
            ''', (datetime.now().isoformat(), feed_id))
    
    conn.commit()
    conn.close()

def update_all_feeds():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM feeds')
    feeds = cursor.fetchall()
    conn.close()
    
    for feed in feeds:
        update_feed(feed['id'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/feeds', methods=['GET'])
def get_feeds():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM feeds ORDER BY created_at DESC')
    feeds = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(feed) for feed in feeds])

@app.route('/feeds', methods=['POST'])
def add_feed():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    feed_data = parse_feed(url)
    if not feed_data:
        return jsonify({'error': 'Invalid RSS feed URL'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO feeds (url, title, last_updated)
            VALUES (?, ?, ?)
        ''', (url, feed_data['title'], datetime.now().isoformat()))
        
        feed_id = cursor.lastrowid
        
        for entry in feed_data['entries']:
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (feed_id, title, link, content, published_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (feed_id, entry['title'], entry['link'], 
                  entry['content'], entry['published']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Feed added successfully', 'feed_id': feed_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Feed already exists'}), 409

@app.route('/feeds/<int:feed_id>', methods=['DELETE'])
def remove_feed(feed_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM articles WHERE feed_id = ?', (feed_id,))
    cursor.execute('DELETE FROM feeds WHERE id = ?', (feed_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Feed removed successfully'})

@app.route('/feeds/<int:feed_id>/refresh', methods=['POST'])
def refresh_feed(feed_id):
    update_feed(feed_id)
    return jsonify({'message': 'Feed refreshed successfully'})

@app.route('/articles', methods=['GET'])
def get_articles():
    feed_id = request.args.get('feed_id')
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT a.*, f.title as feed_title 
        FROM articles a 
        JOIN feeds f ON a.feed_id = f.id 
        WHERE 1=1
    '''
    params = []
    
    if feed_id:
        query += ' AND a.feed_id = ?'
        params.append(feed_id)
    
    if unread_only:
        query += ' AND a.read_status = 0'
    
    query += ' ORDER BY a.published_date DESC LIMIT 100'
    
    cursor.execute(query, params)
    articles = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(article) for article in articles])

@app.route('/articles/<int:article_id>/read', methods=['POST'])
def mark_article_read(article_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE articles SET read_status = 1 WHERE id = ?
    ''', (article_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Article marked as read'})

@app.route('/feeds/export', methods=['GET'])
def export_feeds():
    format_type = request.args.get('format', 'json').lower()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT url, title FROM feeds ORDER BY title')
    feeds = cursor.fetchall()
    conn.close()
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Title', 'URL'])
        for feed in feeds:
            writer.writerow([feed['title'], feed['url']])
        
        output.seek(0)
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=rss_feeds.csv'
        }
    else:
        feeds_data = [{'title': feed['title'], 'url': feed['url']} for feed in feeds]
        return jsonify(feeds_data)

@app.route('/feeds/import', methods=['POST'])
def import_feeds():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    format_type = request.form.get('format', 'json').lower()
    imported_count = 0
    errors = []
    
    try:
        if format_type == 'csv':
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            for row in csv_reader:
                url = row.get('URL') or row.get('url') or row.get('Url')
                title = row.get('Title') or row.get('title') or row.get('TITLE')
                
                if url:
                    result = add_feed_to_db(url, title)
                    if result['success']:
                        imported_count += 1
                    else:
                        errors.append(f"{url}: {result['error']}")
        
        else:  # JSON format
            content = file.read().decode('utf-8')
            feeds_data = json.loads(content)
            
            if isinstance(feeds_data, dict) and 'feeds' in feeds_data:
                feeds_data = feeds_data['feeds']
            
            for feed_data in feeds_data:
                if isinstance(feed_data, dict):
                    url = feed_data.get('url') or feed_data.get('URL')
                    title = feed_data.get('title') or feed_data.get('title')
                elif isinstance(feed_data, str):
                    url = feed_data
                    title = None
                
                if url:
                    result = add_feed_to_db(url, title)
                    if result['success']:
                        imported_count += 1
                    else:
                        errors.append(f"{url}: {result['error']}")
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400
    
    return jsonify({
        'message': f'Import completed. Successfully imported {imported_count} feeds.',
        'imported_count': imported_count,
        'errors': errors
    })

def add_feed_to_db(url, title=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if feed already exists
        cursor.execute('SELECT id FROM feeds WHERE url = ?', (url,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'error': 'Feed already exists'}
        
        # Parse feed to get title if not provided
        if not title:
            feed_data = parse_feed(url)
            if not feed_data:
                conn.close()
                return {'success': False, 'error': 'Invalid RSS feed URL'}
            title = feed_data['title']
        
        # Add feed to database
        cursor.execute('''
            INSERT INTO feeds (url, title, last_updated)
            VALUES (?, ?, ?)
        ''', (url, title, datetime.now().isoformat()))
        
        feed_id = cursor.lastrowid
        
        # If we have feed data, add articles
        feed_data = parse_feed(url)
        if feed_data:
            for entry in feed_data['entries']:
                cursor.execute('''
                    INSERT OR IGNORE INTO articles 
                    (feed_id, title, link, content, published_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (feed_id, entry['title'], entry['link'], 
                      entry['content'], entry['published']))
        
        conn.commit()
        conn.close()
        return {'success': True, 'feed_id': feed_id}
    
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RSS Reader Web Application')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    init_db()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_all_feeds, 'interval', minutes=30)
    scheduler.start()
    
    app.run(debug=args.debug, host=args.host, port=args.port)