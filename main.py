from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import openai
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please check your secrets.")

app = Flask(__name__)
app.secret_key = os.getenv('SESSION_SECRET',
                           'your-secret-key')  # Change this in production

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['PyBot']
users = db['user']
conversations = db['conversation']
messages = db['message']


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = users.find_one({'email': data['email']})
    if user and check_password_hash(user['password_hash'], data['password']):
        session['user_id'] = str(user['_id'])
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if users.find_one({'email': data['email']}):
        return jsonify({
            'success': False,
            'message': 'Email already exists'
        }), 400

    user = {
        'username': data['username'],
        'email': data['email'],
        'password_hash': generate_password_hash(data['password']),
        'created_at': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'last_login': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'roles': ['user'],
        'is_active': True
    }

    result = users.insert_one(user)
    session['user_id'] = str(result.inserted_id)
    return jsonify({'success': True})


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


def load_conversation_history(user_id, toGpt):
    user_id = ObjectId(user_id)  # Convert to ObjectId

    conversation = conversations.find_one(
        {'user_id': user_id, 'status': 'active'},
        sort=[('last_chat', -1)]
    )

    if not conversation:
        return []  

    conversation_id = conversation["_id"]
    message_cursor = messages.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1)

    conversation_history = []
    for msg in message_cursor:
        if msg["sender"] == "system" and not toGpt:
            continue  # Skip system instruction for existing conversations
        conversation_history.append({
            "role": msg["sender"],
            "content": msg["message"]
        })

    return conversation_history  


def save_conversation_history(user_id):
    """Save the conversation history for a specific user."""
    conversations.update_one(
        {'user_id': user_id, 'status': 'active'},
        {'$set': {
            'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        }},
        upsert=True  
    )

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')


@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/chat-history', methods=['GET'])
def chat_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    
    # Check if an active conversation exists
    conversation = conversations.find_one({'user_id': user_id, 'status': 'active'})
    
    if not conversation:
        return jsonify({"history": []})  #  Don't create a conversation, just return an empty list

    # Fetch conversation messages
    conversation_id = conversation["_id"]
    message_cursor = messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)

    conversation_history = []
    for msg in message_cursor:
        if msg["sender"] != "system":  #  Ensure system messages are skipped
            conversation_history.append({
                "role": msg["sender"],
                "content": msg["message"]
            })

    return jsonify({"history": conversation_history})

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({"error": "No user input provided"}), 400

    # Check if a conversation exists
    conversation = conversations.find_one({
        'user_id': user_id,
        'status': 'active'
    })

    is_new_conversation = False  # Track if it's a new conversation

    if not conversation:
        # Create a new conversation only after the first message is sent
        conversation = {
            'user_id': user_id,
            'created_at': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            'status': 'active'
        }
        conversation_result = conversations.insert_one(conversation)
        conversation_id = conversation_result.inserted_id
        is_new_conversation = True  
    else:
        conversation_id = conversation["_id"]
        conversations.update_one(
            {'_id': conversation_id},
            {'$set': {'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))}}
        )

    system_instruction = {
        "role": "system",
        "content": "You are PyBot, an intelligent assistant designed to help learners master Python programming..."
    }

    if is_new_conversation:
        messages.insert_one({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "system",
            "message_type": "text",
            "message": system_instruction["content"]
        })

    # Store user message
    messages.insert_one({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        "sender": "user",
        "message_type": "text",
        "message": user_message
    })

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=load_conversation_history(user_id, True),  # Get latest conversation
            max_tokens=1500,
            temperature=0.4,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )

        gpt_response = response.choices[0].message.content

        # Store AI response
        messages.insert_one({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "assistant",
            "message_type": "text",
            "message": gpt_response
        })

        save_conversation_history(user_id)

        return jsonify({"response": gpt_response})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "error": "Failed to get response from OpenAI. Please check the API key."
        }), 500
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
