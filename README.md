# Jobs Organiser App

A Streamlit application for managing job applications, documents, and career goals.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `secrets.json` file with your API keys:
```json
{
    "OPENAI_API_KEY": "your_openai_api_key",
    "SUPABASE_URL": "your_supabase_url",
    "SUPABASE_API_KEY": "your_supabase_api_key"
}
```

3. Run the app locally:
```bash
streamlit run app.py
```

## Deployment

### Deploying to Streamlit Cloud

1. Push your code to a GitHub repository

2. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account

3. Click "New app" and select your repository

4. Configure your app:
   - Main file path: `app.py`
   - Python version: 3.9 or higher

5. Add your secrets in the Streamlit Cloud dashboard:
   - Go to your app's settings
   - Add the following secrets:
     - `OPENAI_API_KEY`
     - `SUPABASE_URL`
     - `SUPABASE_API_KEY`

6. Deploy your app

### Environment Variables

The following environment variables need to be set in your deployment environment:

- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_API_KEY`: Your Supabase API key

## Features

- Job application tracking
- Document management
- AI-powered job assistant
- Career goals tracking
- Interactive dashboard
- User profile management

## Project Structure

```
jobs_organiser_app/
├── app.py              # Main application file
├── utils.py            # Utility functions
├── dashboard_utils.py  # Dashboard-specific utilities
├── user_portal.py      # User portal functionality
├── jobs_portal.py      # Jobs portal functionality
├── requirements.txt    # Python dependencies
├── .streamlit/         # Streamlit configuration
│   └── config.toml
└── data/              # Data directory
    └── jobs.db        # SQLite database
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 