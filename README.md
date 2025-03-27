# RAWG.io Game Wiki Generator

A Python-based automation system that fetches game data from RAWG.io, generates wiki entries using OpenAI's API, and stores the information in Excel format.

## Features

- Automatically fetches indie game data from RAWG.io
- Generates professional wiki entries using OpenAI's GPT-4o
- Stores complete information in Excel format
- Processes ~800 requests per day (configurable)
- Includes comprehensive error handling and logging

## Requirements

- Python 3.7+
- API Keys for:
  - RAWG.io (get at https://rawg.io/apidocs)
  - OpenAI (get at https://platform.openai.com/)
- Required Python libraries (install via pip):
  - requests
  - openai
  - pandas
  - openpyxl
  - schedule

## Setup

1. Clone this repository
2. Set environment variables:
   ```
   export RAWG_API_KEY="your_rawg_api_key"
   export OPENAI_API_KEY="your_openai_api_key"
   ```
3. Install required packages:
   ```
   pip install requests openai pandas openpyxl schedule
   ```

## Usage

Run the script:

```
python main.py
```

Or start the Flask web interface:

```
python app.py
```

## Deployment to Render.com

This application is ready for deployment on Render.com. There are two ways to deploy:

### Option 1: Deploy using the render.yaml blueprint

1. Fork or clone this repository to your GitHub account
2. Create a new Render account or log into your existing account
3. On the Render dashboard, click "New+" and select "Blueprint"
4. Connect your GitHub account and select your forked/cloned repository
5. Render will detect the render.yaml file and set up the service automatically
6. Add your API keys in the environment variables section:
   - `RAWG_API_KEY`: Your RAWG API key
   - `OPENAI_API_KEY`: Your OpenAI API key
7. Click "Apply" to start the deployment

### Option 2: Manual setup

1. Create a new Web Service on Render
2. Link your GitHub repository
3. Configure the following settings:
   - **Environment**: Python
   - **Build Command**: `./render-build.sh`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --reuse-port main:app`

4. Add environment variables:
   - `RAWG_API_KEY`: Your RAWG API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SESSION_SECRET`: A random string for Flask's session security

5. Choose a plan and deploy!

The application is already configured to pick up Render.com's `PORT` environment variable.

