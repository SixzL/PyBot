# PyBot - Virtual Python Tutor

An AI-powered web application that helps users learn Python through interactive conversations and guided problem-solving.

## Quick Setup

### Prerequisites
- Python 3.8+
- MongoDB Atlas
- OpenAI API account

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=mongodb://localhost:27017/PyBot
SESSION_SECRET=your_secret_key
```

### Run
```bash
python main.py
```
Access at `http://localhost:3000`




## Troubleshooting

- **API Error**: Check API key in `.env`
- **Database Error**: Verify MongoDB connection
- **Port Error**: Change port in `main.py` if 3000 is busy
