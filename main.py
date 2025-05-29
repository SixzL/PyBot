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
    is_completed = conversation and conversation.get('is_completed', False)
    
    # If conversation is already marked as completed, inform the user
    if is_completed:
        # Store user message
        messages.insert_one({
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "user",
            "message": {"type": "text", "content": user_message}
        })
        
        # Generate response about conversation being completed
        completion_response = f"""
This focused session on "{conversation.get('topic')}" has been completed.

If you'd like to start a new challenge, please:
1. Go back to the main conversation
2. Ask a Python question, or
3. Mention a new coding challenge you'd like to tackle

You can also click on the "New conversation" button in the sidebar.
"""
        
        # Store assistant message
        messages.insert_one({
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "assistant",
            "message": {"type": "text", "content": completion_response}
        })
        
        return {
            "response": completion_response,
            "propose_new_chat": False,
            "topic": None
        }
    
    chat_history = load_conversation_history(conversation_id)
    chat_history.append({"role": "user", "content": user_message})
    print(chat_history)
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history,
            max_tokens=1500,
            temperature=0.3,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3,
            tools=ofc.functions,
            tool_choice="auto"
        )

        if response.choices[0].finish_reason == "tool_calls":
            name = response.choices[0].message.tool_calls[0].function.name
            args = response.choices[0].message.tool_calls[0].function.arguments
            args_dict = json.loads(args)
            
            # Store user message
            messages.insert_one({
                "conversation_id": ObjectId(conversation_id),
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "user",
                "message": {"type": "text", "content": user_message}
            })
            
            # Handle mark_problem_solved for focused conversations
            if name == "mark_problem_solved" and is_focused:
                result = ofc.call_function(name, args)
                gpt_response = result['gpt_response']
                next_challenge = args_dict.get('next_challenge')
                
                # Update the conversation to mark it as completed
                conversations.update_one(
                    {'_id': ObjectId(conversation_id)},
                    {'$set': {
                        'is_completed': True,
                        'status': 'completed',
                        'next_challenge_proposed': next_challenge
                    }}
                )
                
                # Store assistant message
                messages.insert_one({
                    "conversation_id": ObjectId(conversation_id),
                    "user_id": user_id,
                    "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                    "sender": "assistant",
                    "message": {"type": "text", "content": gpt_response}
                })
                
                return {
                    "response": gpt_response,
                    "propose_new_chat": True,
                    "topic": next_challenge
                }
            
            # Handle regular propose_new_conversation for normal conversations
            result = ofc.call_function(name, args)
            gpt_response = result['gpt_response']
            topic = result.get('topic')

            # Store the assistant's proposal for new chat
            messages.insert_one({
                "conversation_id": ObjectId(conversation_id),
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "assistant",
                "message": {
                    "type": "invitation",
                    "content": topic,
                    "accepted": False
                }
            })

            return {
                "response": gpt_response,
                "propose_new_chat": True,
                "topic": topic
            }

        # Standard text response
        gpt_response = response.choices[0].message.content

        # Store user message
        messages.insert_one({
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            "sender": "user",
            "message": {"type": "text", "content": user_message}
        })

        # Store assistant message
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


    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "OpenAI API failure"}), 500

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

    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Create a new focused conversation document
    focused_conversation = {
        'user_id': user_id,
        'created_at': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'last_chat': datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        'status': 'active',
        'type': 'focused',  # Indicate this is a focused conversation
        'topic': topic,
        'is_completed': False  # Track if the problem has been completed
    }

    conversation_result = conversations.insert_one(focused_conversation)
    conversation_id = conversation_result.inserted_id

    # Create a tailored system instruction for focused conversations
    system_instruction = {
        "role": "system",
        "content": f"""
You are PyBot, a virtual Python tutor. This is a focused conversation about: {topic}

Your role is to:

1. Guide the user through solving this specific problem/challenge: "{topic}"
2. Help them learn by providing increasingly helpful hints rather than immediate solutions.
3. When you believe they have successfully solved the problem, congratulate them and mark the conversation as completed.
4. At the end, propose a new, slightly more challenging problem they might want to try next.

Remember:
- First, help them understand the problem clearly.
- Provide guidance, not complete solutions.
- If they're stuck, offer increasingly helpful hints.
- When they've solved it, provide positive reinforcement.
- Before ending, suggest a new, related but more challenging problem as their next exercise.
"""
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
            "content": f"""
# Focused Session: {topic}

Welcome to this focused learning session! I'll be helping you work through this problem step by step.

Let's start by understanding the problem clearly. Could you:
1. Explain your understanding of what this problem requires
2. Share any initial thoughts or approaches you're considering
3. Let me know if you'd like me to explain any concepts first

When you're ready, we can begin working on the solution together!
"""
        }
    }
    
    messages.insert_one(welcome_message)

    return jsonify({'success': True, 'conversation_id': str(conversation_id)})


@app.route('/mark-conversation-complete', methods=['POST'])
def mark_conversation_complete():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = ObjectId(session['user_id'])
    data = request.json
    conversation_id = data.get('conversation_id')
    next_challenge = data.get('next_challenge')

    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400

    # Update conversation to mark it as completed
    conversations.update_one(
        {'_id': ObjectId(conversation_id), 'user_id': user_id},
        {'$set': {
            'is_completed': True,
            'status': 'completed',
            'next_challenge_proposed': next_challenge
        }}
    )

    return jsonify({'success': True})

@app.route('/mark-invitation-accepted', methods=['POST'])
def mark_invitation_accepted():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    conversation_id = data.get('conversation_id')
    message_id = data.get('message_id')

    if not conversation_id:
        return jsonify({"error": "Missing conversation_id"}), 400

    try:
        # Update the message in the database
        result = messages.update_one(
            {
                "conversation_id": ObjectId(conversation_id),
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


