# BeaconMind - Mental Health Assessment Chatbot

BeaconMind is an AI-powered chatbot designed to conduct mental health assessments and track patient progress over time.

## 🌟 Key Features

- **Conversational Assessments**: Engages users in dialogue for mental health evaluation
- **Supported Assessments**:
  - PHQ-9 (Depression)
  - GAD-7 (Anxiety)
  - ASQ (Suicide Risk)
  - Custom monitoring questions
- **Patient Monitoring**: Tracks changes over time
- **Automated Scoring**: Assigns scores based on responses
- **Dashboard**: Provides insights for healthcare providers
- **PWA Support**: Accessible as a mobile-friendly web app

## 🏗️ Architecture

Built with Django, using modules for:

- **Accounts**: User authentication
- **Assessments**: Stores and processes assessment data
- **Chat**: Manages conversations with AI models
- **Dashboard**: Displays patient insights

## 💬 How It Works

1. **Evaluates Responses**: Classifies as normal, off-topic, ambiguous, or needing clarification.
2. **Determines Next Step**: Decides follow-up actions.
3. **Scores Assessments**: Calculates results automatically.

## 🚀 Deployment

- Uses Docker for easy setup:

  ```sh
  docker-compose up     # Development
  docker-compose -f docker-compose.prod.yaml up     # Production
