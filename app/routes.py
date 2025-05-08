from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from .models import Bookmark, Tag
from . import db, fetch_metadata

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    selected_tag = request.args.get('tag', None)
    search_query = request.args.get('search', '').strip().lower()
    sort_order = request.args.get('sort', '')

    # Start with bookmarks owned by the current user
    query = Bookmark.query.filter_by(user_id=current_user.id)

    # Filter by tag (if provided)
    if selected_tag:
        query = query.join(Bookmark.tags).filter(Tag.name == selected_tag)

    # Filter by search (if provided)
    if search_query:
        query = query.filter(
            db.or_(
                Bookmark.title.ilike(f'%{search_query}%'),
                Bookmark.url.ilike(f'%{search_query}%')
            )
        )

    # Apply sorting based on the sort_order
    if sort_order == 'title_asc':
        query = query.order_by(func.lower(Bookmark.title).asc())
    elif sort_order == 'title_desc':
        query = query.order_by(func.lower(Bookmark.title).desc())
    elif sort_order == 'date_old':
        query = query.order_by(Bookmark.created_at.asc())
    else:  # default is newest first
        query = query.order_by(Bookmark.created_at.desc())

    bookmarks = query.all()

    # Load all tags for filter UI
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()

    return render_template(
        'index.html',
        bookmarks=bookmarks,
        tags=tags,
        selected_tag=selected_tag,
        sort_order=sort_order
    )

@main.route('/bookmarks', methods=['POST'])
@login_required
def add_bookmark():
    title = request.form.get('title')
    url = request.form.get('url')
    description = request.form.get('description', '').strip()
    tags_raw = request.form.get('tags', '').strip()

    if not title or not url:
        flash('Title and URL are required!', 'error')
        return redirect(url_for('main.index'))

    # Check for existing bookmark for this user
    existing = Bookmark.query.filter_by(url=url, user_id=current_user.id).first()
    if existing:
        flash('This URL already exists in your bookmarks.', 'error')
        return redirect(url_for('main.index'))

    # Fetch metadata only if description is not provided
    if not description:
        metadata = fetch_metadata(url)
        description = metadata['description'] or "No description available"

    # Initialize the new bookmark (NO tag param anymore)
    new_bookmark = Bookmark(title=title, url=url,description=description, user_id=current_user.id)

    # Process tags
    if tags_raw:
        tag_names = [name.strip().lower() for name in tags_raw.split(',') if name.strip()]
        for name in tag_names:
            tag = Tag.query.filter_by(name=name, user_id=current_user.id).first()
            if not tag:
                tag = Tag(name=name, user_id=current_user.id)
                db.session.add(tag)
                db.session.flush()  # Ensure tag.id is available before appending
            new_bookmark.tags.append(tag)

    try:
        db.session.add(new_bookmark)
        db.session.commit()
        flash('Bookmark added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to add bookmark: {e}")
        flash('Error while saving the bookmark. Try again.', 'error')

    return redirect(url_for('main.index'))

@main.route('/delete/<int:bookmark_id>', methods=['POST'])
@login_required
def delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)

    # Ensure only the owner can delete
    if bookmark.user_id != current_user.id:
        flash("You don't have permission to delete this bookmark.", 'error')
        return redirect(url_for('main.index'))

    try:
        # Get the tags before deleting the bookmark
        tags_to_check = list(bookmark.tags)

        db.session.delete(bookmark)
        db.session.commit()

        # Now check each tag: if it's not associated with any bookmark, delete it
        for tag in tags_to_check:
            if not tag.bookmarks:
                db.session.delete(tag)
        db.session.commit()

        flash('Bookmark and unused tags deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the bookmark.', 'error')
        print(f"[ERROR] Failed to delete bookmark or tags: {e}")

    return redirect(url_for('main.index'))

@main.route('/edit/<int:bookmark_id>', methods=['GET'])
@login_required
def edit_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    if bookmark.user_id != current_user.id:
        flash('You are not authorized to edit this bookmark.', 'error')
        return redirect(url_for('main.index'))
    return render_template('edit_bookmark.html', bookmark=bookmark)

@main.route('/update/<int:bookmark_id>', methods=['POST'])
@login_required
def update_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    if bookmark.user_id != current_user.id:
        flash('You are not authorized to update this bookmark.', 'error')
        return redirect(url_for('home'))

    # Update description
    bookmark.description = request.form.get('description')

    # Update tags
    tags_raw = request.form.get('tags', '')
    tag_names = [tag.strip().lower() for tag in tags_raw.split(',') if tag.strip()]
    tags = []
    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name, user_id=current_user.id)
            db.session.add(tag)
        tags.append(tag)
    bookmark.tags = tags

    db.session.commit()
    flash('Bookmark updated successfully!', 'success')
    return redirect(url_for('home'))