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


def load_conversation_history(user_id, toGpt): #check toGpt later
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
                "content": msg["message"]["content"]
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
        "content": """
You are PyBot, a virtual Python tutor.

Your role is to help learners build a deep understanding of Python by:

- **Clearly explaining Python concepts, terminology, and syntax when asked.**
  - You are encouraged to define, describe, and clarify concepts such as what a "for loop" is, what a "list" does, or how "functions" work.

- **Avoiding direct code solutions when the user asks for help writing or generating code.**
  - Instead, guide them with thoughtful questions, small hints, or real-world analogies to encourage critical thinking and problem-solving.
  - Do not provide complete code snippets, formulas, or step-by-step coding solutions.

- **If the user asks for the code or final answer**, politely remind them that you are here to help them learn by thinking it through themselves.

Be friendly, curious, and supportive. Your mission is to help users **understand Python concepts** while **empowering them to write the code themselves through guided discovery.**
"""
    }

    if is_new_conversation:
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

    """ 
        Started to interact with chatbot 
        (the storing messages order logic need to fix)
    """
    try:
        # inputClass = ci.classify_input([{"role": "user", "content":ci.classification_prompt.format(user_input=user_message)}])
        # print("The user input type:")
        # print(inputClass)

        # meta_prompt = ci.select_metaprompt(inputClass)

        # print(meta_prompt.format(user_input=user_message))

        # refinedPrompt = ci.generate_prompt([{"role": "user", "content":meta_prompt.format(user_input=user_message)}])

        # print(refinedPrompt)
        refinedPrompt = user_message

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "error": "Failed to get response from OpenAI. Please check the API key."
        }), 500
    
    chat_history=load_conversation_history(user_id, True)
    chat_history.append({
        "role": "user",
        "content": refinedPrompt
    })
    print("\n\n\n", chat_history)
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

        # print("\n\n\n"+response.choices[0].finish_reason) #access the finish_reason to check whether its a function calling
        # print("\n\n\n"+response.choices[0].message.tool_calls[0].function.name)#access the called function name
        # print(response.choices[0].message.tool_calls[0].function.arguments) #access the function arguements

        if response.choices[0].finish_reason == "tool_calls":
            name = response.choices[0].message.tool_calls[0].function.name
            args = response.choices[0].message.tool_calls[0].function.arguments
            return_propose = ofc.call_function(name, args)
            gpt_response = return_propose['gpt_response']
            topic = return_propose['topic']

            # Store user message
            messages.insert_one({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "user",
                "message" : {
                    "type": "text",
                    "content": user_message,
                    "refined": refinedPrompt
                }
            })

            update_last_conversation(user_id)

            # Store AI response
            messages.insert_one({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "assistant",
                "message": {
                    "type": "text",
                    "content": gpt_response
                }
            })

            messages.insert_one({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "assistant",
                "message": {
                    "type": "invitation",
                    "content": topic,
                    "propose_new_chat": True,
                    "accepted": False
                }
            })

            return jsonify({"response": gpt_response, "propose_new_chat": True, "topic": topic })
        else:
            gpt_response = response.choices[0].message.content

            # Store user message
            messages.insert_one({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "user",
                "message": {
                    "type": "text",
                    "content": user_message,
                    "refined": refinedPrompt
                }
            })


            update_last_conversation(user_id)

            # Store AI response
            messages.insert_one({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
                "sender": "assistant",
                "message": {
                    "type": "text",
                    "content": gpt_response,
                    "propose_new_chat": False,
                    "accepted": False
                }
            })

            print("\n\n\n", gpt_response)
            

            # if gpt_response.get("function_call"):
            #     # Step 4: Extract function name and arguments
            #     function_name = gpt_response.function_call.name
            #     arguments = json.loads(gpt_response.function_call.arguments)                        #EXPERIMENTAL
                
            #     # Example logic: just print what function was chosen
            #     print(f"Function requested: {function_name}")
            #     print(f"With arguments: {arguments}")

            # for tool_call in response.out:
            #     print(tool_call)

            


            # for tool_call in response.output:
            #     if tool_call.type != "function_call":
            #         continue

            #     print("in forloop")
            #     print("\n\n\n"+tool_call.type)
            #     name = tool_call.name
            #     args = json.loads(tool_call.arguments)

            #     result = ofc.call_function(name, args)
            #     # gpt_response.append({
            #     #     "type": "function_call_output",
            #     #     "call_id": tool_call.call_id,
            #     #     "output": str(result)
            #     # })
            #     print({"type": "function_call_output",
            #         "call_id": tool_call.call_id,
            #         "output": str(result)})
                
            print("123 testing")
            return jsonify({"response": gpt_response, "propose_new_chat": False})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "error": "Failed to get response from OpenAI. Please check the API key."
        }), 500
    

    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)


