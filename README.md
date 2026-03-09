# Kindle Scribe Readwise Reader

A lightweight, server-side rendered web app for reading your Readwise Reader articles on a Kindle Scribe. No JavaScript, no images, no bloat -- just text.

## Setup

1. **Clone and install dependencies:**

```bash
git clone https://github.com/ntwkrgr/readwise-reader-personal-site.git
cd readwise-reader-personal-site
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure your Readwise token:**

Get your access token from [readwise.io/access_token](https://readwise.io/access_token), then create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and replace `your_readwise_access_token_here` with your actual token. Optionally set `SECRET_KEY` to any random string (used for flash message session cookies).

3. **Run the server:**

```bash
python app.py
```

The server starts on `0.0.0.0:5555` by default. Access it from your Kindle Scribe at `http://<your-machine-ip>:5555`. Set the `PORT` environment variable in `.env` to change it.

## Usage

- **Article list** shows your reading queue, defaulting to "Inbox". Tap the location tabs (Inbox / Later / Archive) to switch views.
- **Tap an article title** to read it. Content is stripped of images and media for fast loading on e-ink.
- **Archive** an article from the reader view with the Archive button. It disappears from your active list immediately.
- **Refresh** the list manually if you've added new articles from another device.

## Kindle Scribe Browser Notes

This app is designed for the Kindle Scribe's experimental web browser:

- All server-side rendered HTML, zero client-side JavaScript
- Large touch targets for the touchscreen
- High contrast, no color, no animations
- Georgia/serif font stack for comfortable reading
- Minimal page weight to keep load times fast on e-ink
