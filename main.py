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
import python_script.classify_input as ci
import python_script.openai_function_calling as ofc

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


def load_conversation_history(conversation_id): #check toGpt later
    # Ensure ObjectId conversion if needed
    conversation_id = ObjectId(conversation_id)

    conversation = conversations.find_one({'_id': conversation_id})
    if not conversation:
        return []

    message_cursor = messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)

    conversation_history = []
    for msg in message_cursor:
        # Include system messages in the conversation history
        conversation_history.append({
            "role": msg["sender"],
            "content": msg["message"]["content"]
        })

    return conversation_history


def update_last_conversation(user_id):
    """update the last conversation time for a specific user."""
    conversations.update_one(
        {'user_id': user_id, 'status': 'active'},
        {'$set': {
            'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        }},
        upsert=True  
    )

@app.route('/')
def home():
    print(123)
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', conversation_id=None)


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

@app.route('/chat-history', methods=['POST'])
def chat_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    conversation_id = data.get('conversation_id')

    if conversation_id:
        conversation = conversations.find_one({'_id': ObjectId(conversation_id), 'user_id': ObjectId(session['user_id'])})
        if not conversation:
            return jsonify({"history": []})
    else:
        # Default to latest active
        conversation = conversations.find_one({'user_id': ObjectId(session['user_id']), 'status': 'active'})

    if not conversation:
        return jsonify({"history": []})

    message_cursor = messages.find({"conversation_id": conversation["_id"]}).sort("timestamp", 1)

    conversation_history = []
    for msg in message_cursor:
        if msg["sender"] == "system":
            continue
            
        message_data = {
            "role": msg["sender"],
            "content": msg["message"]["content"],
            "type": msg["message"].get("type", "text")  # Default to "text" if type not specified
        }
        
        # Include message ID and accepted status for invitation messages
        if msg["message"].get("type") == "invitation":
            message_data["_id"] = str(msg["_id"])
            message_data["accepted"] = msg["message"].get("accepted", False)
            message_data["submitted_code"] = msg["message"].get("submitted_code")  # Include submitted_code
            
        conversation_history.append(message_data)

    return jsonify({"history": conversation_history})


@app.route('/conversation', methods=['GET', 'POST'])
def new_conversation():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({"error": "No user input provided"}), 400

    # Generate a title for the new conversation
    try:
        conversation_title = ofc.generate_chat_title(user_message)
    except Exception as e:
        print(f"Error generating title: {str(e)}")
        conversation_title = "New Conversation"

    new_conversation_doc = {
        'user_id': user_id,
        'created_at': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'status': 'active',
        'title': conversation_title
    }

    conversation_result = conversations.insert_one(new_conversation_doc)
    conversation_id = conversation_result.inserted_id

    system_instruction = {
        "role": "system",
        "content": """
You are PyBot, a virtual Python tutor.

Your role is to help learners build a deep understanding of Python by:

- **Clearly explaining Python concepts, terminology, and syntax when asked.**
  - You are encouraged to define, describe, and clarify concepts such as what a "for loop" is, what a "list" does, or how "functions" work.

- **Avoiding direct code solutions when the user asks for help writing or generating code.**
  - Instead, guide them with thoughtful questions, small hints, or real-world analogies to encourage critical thinking and problem-solving.
  - Do not provide complete code snippets, formulas, or step-by-step coding solutions.

- **If the user asks for the code or final answer**, politely remind them that you are here to help them learn by thinking it through themselves.

- **If the user asks non-Python-related questions**, DO NOT ANSWER the question and kindly remind them that you are here to help them with Python Programming.

Be friendly, curious, and supportive. Your mission is to help users **understand Python concepts** while **empowering them to write the code themselves through guided discovery.**
"""
    }

    messages.insert_one({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        "sender": "system",
        "message": {
            "type": "text",
            "content" : system_instruction["content"]
        } 
    })

    result = continue_conversation_logic(user_id, conversation_id, user_message)
    result["conversation_id"] = str(conversation_id)
    result["title"] = conversation_title
    return jsonify(result)

@app.route('/conversation/<conversation_id>', methods=['POST'])
def continue_conversation(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    user_message = request.json.get('message')

    if not user_message:
        return jsonify({"error": "No user input provided"}), 400

    # Verify the conversation belongs to the user
    conversation = conversations.find_one({'_id': ObjectId(conversation_id), 'user_id': user_id})
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    # Update last_chat timestamp
    conversations.update_one(
        {'_id': ObjectId(conversation_id)},
        {'$set': {'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))}}
    )

    # Continue processing as a normal chat
    result = continue_conversation_logic(user_id, conversation_id, user_message)
    result["conversation_id"] = str(conversation_id)
    return jsonify(result)

@app.route('/conversation/<conversation_id>', methods=['GET'])
def view_conversation_page(conversation_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', conversation_id=conversation_id)
    
def continue_conversation_logic(user_id, conversation_id, user_message):
    # Check if this is a focused conversation
    conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
    is_focused = conversation and conversation.get('type') == 'focused'
    
    chat_history = load_conversation_history(conversation_id)
    chat_history.append({"role": "user", "content": user_message})
    print(chat_history)
    try:
        # Select functions based on conversation type
        if is_focused:
            tools = ofc.focused_functions
        else:
            tools = ofc.normal_functions

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history,
            max_tokens=1500,
            temperature=0.3,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3,
            tools=tools,
            tool_choice="auto"
        )
        print(response)
        # Store the assistant's message in memory first
        assistant_message = response.choices[0].message
        chat_history.append({
            "role": "assistant",
            "content": assistant_message.content if assistant_message.content else ""
        })

        if response.choices[0].finish_reason == "tool_calls":
            name = assistant_message.tool_calls[0].function.name
            args = assistant_message.tool_calls[0].function.arguments
            
            # Handle regular propose_new_conversation for normal conversations
            result = ofc.call_function(name, args)
            gpt_response = result['gpt_response']
            topic = result.get('topic')
            submitted_code = result.get('submitted_code')  # Get submitted_code from result

            # Store the assistant's response and invitation in database
            # Only store the invitation message since it contains both the response and the invitation
            invitation_message = {
                "conversation_id": ObjectId(conversation_id),
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "assistant",
                "message": {
                    "type": "invitation",
                    "content": topic,  # Just use the topic
                    "accepted": False,
                    "submitted_code": submitted_code,  # Include submitted_code in the message
                    "response": gpt_response  # Include the assistant's response in the invitation message
                }
            }
            
            # Insert the message and get its ID
            message_result = messages.insert_one(invitation_message)
            message_id = str(message_result.inserted_id)

            return {
                "response": gpt_response,
                "propose_new_chat": True,
                "topic": topic,
                "message_id": message_id,
                "submitted_code": submitted_code  # Include submitted_code in the response
            }

        # Standard text response
        gpt_response = assistant_message.content

        # Store user message and assistant response in database
        messages.insert_one({
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "user",
            "message": {"type": "text", "content": user_message}
        })

        messages.insert_one({
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "assistant",
            "message": {"type": "text", "content": gpt_response}
        })

        return {
            "response": gpt_response,
            "propose_new_chat": False,
            "topic": None
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "error": "OpenAI API failure"
        }

@app.route('/conversations', methods=['GET'])
def list_conversations():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    user_conversations = conversations.find({'user_id': user_id}).sort('last_chat', -1)

    conversation_list = []
    for conv in user_conversations:
        conversation_data = {
            'conversation_id': str(conv['_id']),
            'created_at': conv['created_at'].isoformat(),
            'last_chat': conv['last_chat'].isoformat() if 'last_chat' in conv else conv['created_at'].isoformat(),
            'title': conv.get('title', None)  # Include the title
        }
        
        # Include additional fields if they exist
        if 'type' in conv:
            conversation_data['type'] = conv['type']
        
        if 'topic' in conv:
            conversation_data['topic'] = conv['topic']
            
        if 'is_completed' in conv:
            conversation_data['is_completed'] = conv['is_completed']
            
        conversation_list.append(conversation_data)

    return jsonify({'conversations': conversation_list})

@app.route('/create-focused-conversation', methods=['POST'])
def create_focused_conversation():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    data = request.json
    topic = data.get('topic')
    submitted_code = data.get('submitted_code')  # Get submitted code

    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Create a new focused conversation document
    focused_conversation = {
        'user_id': user_id,
        'created_at': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'status': 'active',
        'type': 'focused',
        'topic': topic,
        'is_completed': False,
        'initial_code': submitted_code  # Store the initial code
    }

    conversation_result = conversations.insert_one(focused_conversation)
    conversation_id = conversation_result.inserted_id

    # Get the system instruction using both topic and code
    system_instruction = {
        "role": "system",
        "content": ofc.get_system_instruction(topic, submitted_code)
    }

    # Store the system instruction
    messages.insert_one({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        "sender": "system",
        "message": {
            "type": "text",
            "content" : system_instruction["content"]
        } 
    })

    # Add initial message welcoming the user to the focused conversation
    welcome_message = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        "sender": "assistant",
        "message": {
            "type": "text",
            "content": ofc.generate_welcome_message(
                topic=topic,
                submitted_code=submitted_code,
                conversation_id=str(conversation_id)
            )
        }
    }
    
    messages.insert_one(welcome_message)

    return jsonify({'success': True, 'conversation_id': str(conversation_id)})

@app.route('/mark-invitation-accepted', methods=['POST'])
def mark_invitation_accepted():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        conversation_id = data.get('conversation_id')
        message_id = data.get('message_id')

        if not conversation_id or not message_id:
            return jsonify({"error": "Missing conversation_id or message_id"}), 400

        # Validate ObjectId format
        try:
            conv_id = ObjectId(conversation_id)
            msg_id = ObjectId(message_id)
        except:
            return jsonify({"error": "Invalid ID format"}), 400

        # Update the specific message using its ID
        result = messages.update_one(
            {
                "_id": msg_id,
                "conversation_id": conv_id,
                "message.type": "invitation"
            },
            {'$set': {'message.accepted': True}}
        )

        if result.modified_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Message not found or already accepted'}), 404

    except Exception as e:
        print(f"Error updating invitation status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)


