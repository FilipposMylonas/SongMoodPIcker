# Music Mood Picker

**Get personalized Spotify song recommendations based on your mood**

[**Features**](#features) · [**Installation**](#installation) · [**Usage**](#usage) · [**Deploy to Production**](#deploy-to-production) · [**Feedback and Issues**](#feedback-and-issues)

## Features

- **Mood-based Song Recommendations**: Input your mood and receive 10 personalized song recommendations from Spotify.
- **Cohere AI Integration**: Use Cohere to classify user input into moods.
- **Spotify API Integration**: Fetch song recommendations directly from Spotify based on mood attributes (energy, valence, genre).
- **History Tracking**: View your past mood inputs and recommendations.
- **Clear History**: Easily clear previous entries from your session history.
- **Responsive UI**: Optimized for both desktop and mobile devices.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/music-mood-picker.git
   cd music-mood-picker

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   
3. **Install dependencies**:
   ```bash
   pip install flask requests python-dotenv spotipy cohere

5. **Run the application** :
   ```bash
   python app.py

6. **Access the application:
   Open your browser and go to http://localhost:5000.**