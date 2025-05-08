from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from flask_login import current_user, login_required
from dotenv import load_dotenv  # Import dotenv
from sqlalchemy.exc import OperationalError
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    # Set the database path to the root directory of the project
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bookmarks.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_fallback_key')  # Use environment variable
    app.debug = True
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Import models here to avoid circular imports
    from .models import User, Tag, Bookmark

    # Create database tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    @app.route('/bookmarks', methods=['GET'])
    def get_bookmarks():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        bookmarks = Bookmark.query.paginate(page=page, per_page=per_page)
        bookmarks_list = [
            {'id': bookmark.id, 'title': bookmark.title, 'url': bookmark.url, 'tags': bookmark.tag.name if bookmark.tag else None}
            for bookmark in bookmarks.items
        ]
        return jsonify(bookmarks_list)

    @app.route('/home')
    @login_required
    def home():
        from .models import Bookmark  # Import the Bookmark model

        # Query bookmarks for the currently logged-in user
        bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()

        # Pass the filtered bookmarks to the template
        return render_template('index.html', bookmarks=bookmarks)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the error
        app.logger.error(f"An error occurred: {e}")
        return "An internal server error occurred.", 500
    
    @app.errorhandler(OperationalError)
    def handle_db_error(e):
        app.logger.error(f"Database error: {e}")
        return "A database error occurred.", 500

    return app

def fetch_metadata(url):
    try:
        # Make an HTTP GET request with a timeout
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = soup.title.string.strip() if soup.title else None

        # Extract description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()
        else:
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                description = og_desc['content'].strip()

        # Fallback: Extract the first paragraph text if no description is found
        if not description:
            first_paragraph = soup.find('p')
            if first_paragraph:
                description = first_paragraph.get_text().strip()

        print(f"[DEBUG] Fetched metadata for {url}: title={title}, description={description}")
        return {
            'title': title,
            'description': description
        }
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout occurred while fetching metadata for URL: {url}")
        return {'title': None, 'description': None}
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error fetching metadata for URL {url}: {e}")
        return {'title': None, 'description': None}
            
@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))