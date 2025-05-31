import json
import openai
import jsonify
from bson import ObjectId
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['PyBot']
messages = db['message']

# Function definitions for OpenAI function calling
normal_functions = [
    {
        "type": "function",
        "function": {
            "name": "propose_new_conversation",
            "description": 
'''
Use this function whenever the user's message includes, directly or indirectly, a question, statement, or request that can be interpreted as a coding challenge, algorithmic exercise, or programming problem statement.
The function creates a focused learning conversation that encourages critical thinking through hints and guided discovery.

Common trigger scenarios:
- Programming challenges ("Write a function that...")
- Algorithm problems ("How do you solve...?")
- Data structure operations ("Implement a binary tree...")
- Optimization questions ("How to improve this solution?")
- Concept explanations ("What is a for loop?", "How do lists work?")

The function will:
- Keep the conversation focused on the specific topic
- Provide hints instead of direct solutions
- Encourage critical thinking and problem-solving
- Guide users to discover solutions themselves

Parameter Usage Guidelines:
- topic: Always required - specifies the learning focus area
- problem_statement: Required - must directly relate to the topic and be specific enough to guide learning
- submitted_code: For code examples, following this STRICT PRIORITY ORDER:
  1. HIGHEST PRIORITY: If the user provides code in their message, use that code
  2. MEDIUM PRIORITY: If discussing an existing code example from the conversation, use that code
  3. LOWEST PRIORITY: If no code is available from priorities 1 or 2, you MUST generate a simple, beginner-friendly example that demonstrates the concept

NEVER return an empty string for submitted_code - always provide relevant code that helps teach the concept according to the priority order above.
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic/exercise/problem to focus on. For example, 'For Loop in Python (beginner)', 'Two Sum', 'Roman to Integer', 'Sudoku Solver'"
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "A specific, well-defined problem or learning objective that directly relates to the topic. Must follow these guidelines:\n1. MUST be directly related to the specified topic\n2. MUST be specific enough to guide implementation\n3. MUST include clear requirements or expected outcomes\n\nExamples of good alignment:\nTopic: 'For Loop in Python (beginner)'\n- Good: 'Write a program to sum all even numbers from 1 to 100 using a for loop'\n- Bad: 'Create a calculator program' (too broad, not focused on for loops)\n\nTopic: 'Recursive Functions'\n- Good: 'Implement a recursive function to calculate the nth Fibonacci number'\n- Bad: 'Write a function to sort numbers' (doesn't specify recursion)\n\nTopic: 'Python Lists'\n- Good: 'Create a function that finds the second largest element in a list'\n- Bad: 'Work with data structures' (too vague, not list-specific)",
                    },
                    "submitted_code": {
                        "type": "string",
                        "description": "The code to analyze or exercise to work on. Follow this STRICT PRIORITY ORDER:\n1. HIGHEST PRIORITY: User's submitted code if provided in their message\n2. MEDIUM PRIORITY: Relevant code from conversation context\n3. LOWEST PRIORITY: If no code is available from priorities 1 or 2, generate a beginner-friendly example that demonstrates the topic\n\nNEVER return an empty string - you MUST provide code following the priority order above.",
                    },
                },
                "required": ["topic", "problem_statement"]
            }
        }
    }
]

focused_functions = [
    {
        "type": "function",
        "function": {
            "name": "focused_placeholder",
            "description": 
'''
DO NOT USE THIS FUNCTION.
This is a placeholder function that should never be triggered or called.
This function exists only for structural purposes.
If you're seeing this description, ignore it completely.
Never call or use this function under any circumstances.
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "placeholder": {
                        "type": "string",
                        "description": "This parameter should never be used."
                    }
                },
                "required": ["placeholder"]
            }
        }
    }
]

# Template for proposing a new conversation
propose_template = """\
I see you're interested in {topic}. Let's work through this together.

{code_section}

I'll guide you through:
1. Understanding the problem and its requirements
2. Breaking down the solution into manageable steps
3. Identifying key concepts and potential challenges

Let me know if you'd like to begin!
"""

# Template for proposing a next challenge
next_challenge_template = """\
Congratulations on solving this problem! 🎉

Based on what you've learned, here's a slightly more challenging problem you might want to try next:

# {next_challenge}

Would you like to:
1. Start a new focused session on this challenge
2. Continue exploring other Python concepts

Let me know what you'd prefer!
"""

# Example function implementations
def get_system_instruction(topic, problem_statement, submitted_code=None):
    base_instruction = f'''You are PyBot, an educational coding mentor focused specifically on teaching {topic}.

Current Learning Objective:
{problem_statement}

Core Principles:
1. QUESTION PACING
- Ask only ONE question at a time
- Wait for the user's complete answer before asking the next question
- If the user's answer is incomplete or unclear, follow up on that specific point before moving on
- Never overwhelm the user with multiple questions at once

2. PROBLEM SCOPE
- Focus ONLY on solving the current problem statement
- Keep discussion centered on {topic} concepts needed for the solution
- If user asks about unrelated topics, politely redirect to the current problem
- Guide user step-by-step towards solving {problem_statement}

3. CONVERSATION FLOW
- Start with one fundamental question about their understanding of the problem
- Based on their response, ask one targeted follow-up question
- Progress systematically through concepts needed to solve the problem
- Ensure each step builds towards the final solution'''

    if submitted_code:
        code_specific_instruction = f'''
4. CODE REVIEW APPROACH
- Begin with a single, specific question about their code in relation to {problem_statement}
- Examples (choose only ONE):
  * "How does this part of your code address [specific aspect of problem]?"
  * "What was your approach for implementing [specific requirement]?"
  * "How would your solution handle [specific case from problem]?"

5. IMPROVEMENT GUIDANCE
- After receiving a complete answer to your question, provide ONE targeted hint
- Keep hints focused on requirements from the problem statement
- Wait for their response before offering another hint
- Focus on one aspect of improvement at a time

Current Code Context:
```python
{submitted_code}
```

Remember: 
- One question at a time
- Wait for complete answers
- Stay focused on the current problem statement
- Only move to the next concept when the current one is understood
'''
        return base_instruction + code_specific_instruction
    else:
        general_instruction = '''
4. GUIDED DISCOVERY
- Start with one foundational question about the problem requirements
- Wait for the user's understanding before proceeding
- Break down the problem into single, manageable steps
- Use the Socratic method with ONE question at a time

5. LEARNING VALIDATION
- Ask ONE specific question to verify understanding of each requirement
- If understanding is incomplete, stay on that topic
- Only progress when current concept is clear
- Focus on depth over breadth
'''
        return base_instruction + general_instruction

def propose_new_conversation(topic, problem_statement, submitted_code=None):
    print("OFC: propose_new_conversation")
    print(f"\n\n\nTopic: {topic}")
    print(f"Problem Statement: {problem_statement}")
    print(f"Submitted Code:\n{submitted_code}")
    
    # Get context-aware system instruction
    system_instruction = get_system_instruction(topic, problem_statement, submitted_code)
    
    try:
        prompt = f"""Based on the provided system instruction and problem statement:

Problem: {problem_statement}

1. If this is user-submitted code or code from conversation:
   - Start by asking 2-3 questions about the current implementation
   - Guide them to discover potential improvements through hints
   - Help them think about edge cases and testing
   - Focus on {topic}-specific optimizations

2. If this is a generated exercise:
   - Explain why this exercise is good for learning {topic}
   - Break down the key concepts they'll need to understand
   - Provide initial hints about approaching the problem
   - Suggest what they should think about before starting

Remember: 
- No direct solutions - use questions and hints to guide discovery
- Focus on understanding and learning rather than just completing the task
- Help them develop problem-solving skills"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3,
        )

        return {
            "topic": topic,
            "problem_statement": problem_statement,
            "submitted_code": submitted_code,
            "gpt_response": response.choices[0].message.content,
            "invite": True,
            "is_focused": False  # This is not a focused conversation yet
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "error": "Failed to get response from OpenAI. Please check the API key."
        }), 500

def generate_chat_title(user_message):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a title generator. Generate a short, descriptive title (maximum 50 characters) for a chat based on the user's first message. The title should be concise but informative about the topic or question being discussed."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=60,
            temperature=0.7,
            top_p=1.0
        )
        
        title = response.choices[0].message.content.strip()
        # Ensure title is not too long
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        print(f"Error generating title: {str(e)}")
        return "New Conversation"

def call_function(name, args_str):
    args = json.loads(args_str)
    print(f"Function called: {name}")
    print(f"Arguments: {args}")
    
    if name == "propose_new_conversation":
        return propose_new_conversation(**args)
    else:
        print(f"Unknown function: {name}")
        return {"error": f"Unknown function: {name}"}

def generate_welcome_message(topic, submitted_code=None, conversation_id=None):
    """Generate a personalized welcome message for a focused conversation."""
    try:
        # Format code section for context
        code_context = f"""Here's the code context we'll be working with:

```python
{submitted_code}
```""" if submitted_code else "We'll start from scratch with this topic."

        # Fetch and prepare chat history context if conversation_id is provided
        history_context = ""
        if conversation_id:
            # Get the last few messages from the previous conversation
            previous_messages = messages.find({
                "conversation_id": ObjectId(conversation_id),
                "sender": {"$in": ["user", "assistant"]},  # Only user and assistant messages
                "message.type": "text"  # Only text messages
            }).sort("timestamp", -1).limit(3)  # Get last 3 messages
            
            if previous_messages:
                history_context = "\nContext from previous conversation:\n"
                for msg in previous_messages:
                    role = msg["sender"]
                    content = msg["message"]["content"]
                    history_context += f"{role}: {content}\n"

        system_prompt = f"""You are creating a focused welcome message for a Python learning session about {topic}.

Your welcome message must:
1. Be professional but approachable (avoid being overly playful or formal)
2. Briefly acknowledge the topic
3. ALWAYS include the code context in a Python code block
4. After the code, provide ONE small hint or observation about the code
5. Keep the entire message concise (max 4-5 lines total)

Format:
- Start with a brief welcome
- Show the code block
- End with one small hint/observation

Remember:
- No emojis or exclamation marks
- No questions or calls to action
- Just state what we'll be working on and provide the hint"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""Topic: {topic}
Code Context: {code_context}
{history_context}

Generate a welcoming message that sets the right tone for this focused learning session."""}
            ],
            max_tokens=500,
            temperature=0.7,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error generating welcome message: {str(e)}")
        # Fallback to a simple welcome message if generation fails
        return f"Welcome to our session on {topic}. {code_context}"