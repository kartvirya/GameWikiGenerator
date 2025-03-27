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

