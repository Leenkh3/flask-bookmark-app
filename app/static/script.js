const form = document.getElementById('bookmark-form');
const list = document.getElementById('bookmark-list');

// Fetch bookmarks on load
window.onload = () => {
  fetch('/bookmarks')
    .then(res => res.json())
    .then(data => {
      list.innerHTML = '';
      data.forEach(b => addBookmarkToDOM(b));
    });
};

// Handle form submission
form.onsubmit = async (e) => {
  e.preventDefault();

  const title = document.getElementById('title').value;
  const url = document.getElementById('url').value;
  const tags = document.getElementById('tags').value;

  const response = await fetch('/bookmarks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, url, tags })
  });

  if (response.ok) {
    const bookmark = await response.json();
    addBookmarkToDOM(bookmark);
    form.reset();
  } else {
    alert('Failed to add bookmark.');
  }
};

// Helper function to show bookmark in UI
function addBookmarkToDOM(bookmark) {
  const div = document.createElement('div');
  div.className = 'bg-white p-4 shadow rounded';
  div.setAttribute('data-id', bookmark.id); // Add a unique identifier for the bookmark

  div.innerHTML = `
    <h2 class="text-xl font-semibold">${bookmark.title}</h2>
    <a href="${bookmark.url}" target="_blank" class="text-blue-600 underline">${bookmark.url}</a>
    <p class="mt-2 text-sm text-gray-500">${bookmark.tags}</p>
    <button class="delete-btn text-red-500 mt-2">Delete</button>
  `;

  // Add event listener for the delete button
  const deleteButton = div.querySelector('.delete-btn');
  deleteButton.onclick = () => {
    confirmDelete(bookmark.id); // Call confirmDelete to show confirmation dialog
  };

  list.prepend(div);
}

// Function to confirm deletion
function confirmDelete(bookmarkId) {
  const userConfirmed = confirm("Are you sure you want to delete this bookmark?");
  if (userConfirmed) {
    deleteBookmark(bookmarkId);
  }
}

// Function to delete a bookmark
async function deleteBookmark(bookmarkId) {
  const response = await fetch(`/delete/${bookmarkId}`, { method: 'POST' });
  if (response.ok) {
    // Remove the bookmark from the DOM
    const bookmarkElement = document.querySelector(`[data-id="${bookmarkId}"]`);
    if (bookmarkElement) {
      bookmarkElement.remove();
    }
    alert("Bookmark deleted successfully.");
  } else {
    alert("Failed to delete the bookmark.");
  }
}