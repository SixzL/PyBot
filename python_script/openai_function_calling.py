import json
import openai
import jsonify
from bson import ObjectId
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['PyBot']
messages = db['message']
conversations = db['conversation']

# Function definitions for OpenAI function calling
normal_functions = [
    {
        "type": "function",
        "function": {
            "name": "propose_new_conversation",
            "description": 
'''
Use this function to create a focused learning conversation in ANY of these scenarios:

1. DIRECT INDICATORS:
- User explicitly asks for help with a coding problem
- User mentions wanting to solve or implement something
- User shares code they want help with

2. IMPLICIT INDICATORS (VERY IMPORTANT):
- User expresses confusion or uncertainty ("I don't know", "I don't understand")
- User asks the same question multiple times
- User's responses show they're struggling with concepts
- Multiple back-and-forth exchanges without clear progress
- User seems stuck on a particular concept or implementation

3. LEARNING PATTERNS:
- User is asking about specific programming concepts
- Discussion naturally evolves into a coding challenge
- User shows interest in practicing or implementing something
- Conversation becomes focused on a particular programming topic

4. GUIDANCE NEEDS:
- User needs structured step-by-step assistance
- Topic would benefit from hands-on coding practice
- Complex concept that requires guided implementation
- User would benefit from practical application of theory

The function creates a focused learning conversation that:
1. Provides clear problem statement and requirements
2. Breaks down complex topics into manageable steps
3. Guides through implementation with targeted questions
4. Encourages critical thinking and problem-solving

IMPORTANT:
- Don't wait for explicit requests - recognize when users need structured guidance
- Be proactive in transitioning to focused learning when users show signs of struggling
- Create focused conversations early when users express uncertainty or confusion
- Use this to provide structure when free-form discussion isn't helping user progress

Parameter Usage Guidelines:
- topic: Always required - specifies the learning focus area
- problem_statement: Required - must directly relate to the topic and be specific enough to guide learning
- submitted_code: Only use code directly provided in the user's current message. If no code is in their message, this should be an empty string.
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic/exercise/problem to focus on. For example, 'For Loop in Python', 'Two Sum', 'Roman to Integer', 'Sudoku Solver'"
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "A specific, well-defined problem or learning objective that directly relates to the topic. Must follow these guidelines:\n1. MUST be directly related to the specified topic\n2. MUST be specific enough to guide implementation\n3. MUST include clear requirements or expected outcomes\n4. MUST include examples of input and output\n\nExamples of good alignment:\nTopic: 'For Loop in Python (beginner)'\n- Good: 'Write a program to sum all even numbers from 1 to 100 using a for loop.\nExample:\nInput: None (uses numbers 1 to 100)\nOutput: 2550 (sum of 2 + 4 + 6 + ... + 98 + 100)'\n- Bad: 'Create a calculator program' (too broad, not focused on for loops)\n\nTopic: 'Recursive Functions'\n- Good: 'Implement a recursive function to calculate the nth Fibonacci number.\nExample:\nInput: n = 6\nOutput: 8 (Fibonacci sequence: 1,1,2,3,5,8)'\n- Bad: 'Write a function to sort numbers' (doesn't specify recursion)\n\nTopic: 'Python Lists'\n- Good: 'Create a function that finds the second largest element in a list.\nExample:\nInput: [10, 5, 8, 12, 3]\nOutput: 10 (12 is largest, 10 is second largest)'\n- Bad: 'Work with data structures' (too vague, not list-specific)",
                    },
                    "submitted_code": {
                        "type": "string",
                        "description": "ONLY use code that was directly provided by the user in their message. Do not generate example code or use code from elsewhere in the conversation.\n\nIf the user has not provided any code in their message, this should be an empty string.\n\nThis parameter is meant to capture the user's actual code attempt, even if it contains bugs or errors, as it will be used as a starting point for the learning discussion.",
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
            "name": "problem_solved",
            "description": 
'''
CRITICAL: This function should NEVER be called just because the user says "mark as complete" or similar phrases.

This function should be called ONLY when ALL of the following conditions are met:
1. The user has provided a complete solution in code form
2. You have thoroughly verified that their code correctly solves ALL requirements of the problem
3. You have tested their solution against the problem's example cases
4. You have verified their solution handles edge cases
5. Their code runs without any syntax errors or major runtime issues
6. Their solution demonstrates clear understanding of the core concepts

VERIFICATION REQUIREMENTS:
- You MUST verify the solution works for ALL test cases given in the problem
- You MUST verify the solution follows ALL constraints specified in the problem
- You MUST check that the code handles edge cases appropriately
- You MUST ensure the solution uses the required concepts/approaches specified in the problem

STRICTLY PROHIBITED:
- DO NOT call this function if the user just asks to mark it complete
- DO NOT call this function if you haven't seen their complete solution
- DO NOT call this function if you haven't verified the solution against all requirements
- DO NOT call this function if the solution has any errors or missing requirements
- DO NOT call this function based on user claims without seeing their code

The function will:
1. Mark the current focused conversation as completed
2. Analyze the user's learning progression
3. Create a new focused conversation with a harder problem

Note: For solutions that work correctly but could be optimized:
- DO mark the problem as solved first (call this function)
- Then optionally suggest optimizations in the next conversation
- Don't hold back marking a problem as solved just for minor optimization possibilities
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic of the current focused conversation"
                    },
                    "current_problem": {
                        "type": "string",
                        "description": "The problem statement that was just solved"
                    },
                    "submitted_code": {
                        "type": "string",
                        "description": "The initial code submitted by the user when creating the focused conversation. This may contain mistakes that can guide the generation of the next problem."
                    },
                    "history_context": {
                        "type": "string",
                        "description": "The conversation history context to be used in generating the next problem"
                    }
                },
                "required": ["topic", "current_problem", "submitted_code", "history_context"]
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

CRITICAL INSTRUCTION:
NEVER mark a problem as complete just because the user asks. You MUST:
1. See their complete solution code
2. Verify it works for ALL test cases
3. Check ALL problem requirements are met
4. Verify it handles edge cases
5. Ensure it demonstrates understanding

If a user says "mark as complete" or similar WITHOUT showing their code:
- DO NOT call problem_solved
- Instead, ask to see their solution first
- Explain that you need to verify it meets all requirements

Core Principles:
1. SOLUTION VALIDATION
- IMMEDIATELY validate any complete solution against ALL problem requirements
- If solution is correct AND verified, call problem_solved
- If solution has ANY missing requirements or errors, provide specific feedback
- Never mark a solution complete without thorough verification
- Only proceed with problem_solved after ALL verification steps pass

2. HANDLING UNCERTAINTY
- When user expresses uncertainty ("I don't know", "Not sure", etc.):
  * Start with the SMALLEST possible concept they need to understand
  * NEVER reveal multiple steps or the full solution path
  * Give only ONE hint or explanation at a time
  * Wait for user's response before providing the next hint
  * Use analogies or simpler examples to build understanding
- Focus on building confidence through small successes

3. QUESTION PACING
- Ask only ONE question at a time
- Wait for the user's complete answer before asking the next question
- If the user's answer is incomplete or unclear, follow up on that specific point before moving on
- Never overwhelm the user with multiple questions at once
- When user is stuck, break down the current step into smaller parts

4. PROBLEM SCOPE
- Focus ONLY on solving the current problem statement
- Keep discussion centered on {topic} concepts needed for the solution
- If user asks about unrelated topics, politely redirect to the current problem
- Guide user step-by-step towards solving {problem_statement}

5. CONVERSATION FLOW
- Start with one fundamental question about their understanding of the problem
- Based on their response, ask one targeted follow-up question
- Progress systematically through concepts needed to solve the problem
- Ensure each step builds towards the final solution
- NEVER skip steps or jump ahead in the solution process

6. GUIDED DISCOVERY
- Start with one foundational question about the problem requirements
- Wait for the user's understanding before proceeding
- Break down the problem into single, manageable steps
- Use the Socratic method with ONE question at a time
- When explaining concepts:
  * Give ONE piece of information at a time
  * Use simple examples for complex concepts
  * Wait for user's understanding before moving on
  * Avoid revealing future steps or full solution path

7. LEARNING VALIDATION
- If understanding is incomplete, stay on that topic
- Only progress when current concept is clear
- Focus on depth over breadth
- Verify understanding through targeted questions'''

    if submitted_code:
        code_specific_instruction = f'''
8. CODE REVIEW APPROACH
- First verify if the submitted code solves the problem correctly
- If it does, use problem_solved immediately without any additional questions
- If it doesn't, begin with a single, specific question about their approach
- Examples (choose only ONE):
  * "How does this part of your code address [specific aspect of problem]?"
  * "What was your approach for implementing [specific requirement]?"
  * "How would your solution handle [specific case from problem]?"

9. IMPROVEMENT GUIDANCE
- Only proceed with improvement guidance if the solution is incorrect
- After receiving a complete answer to your question, provide ONE targeted hint
- Keep hints focused on requirements from the problem statement
- Wait for their response before offering another hint
- Focus on one aspect of improvement at a time

Current Code Context:
```python
{submitted_code}
```

Remember: 
- Always check for correct solutions first
- Call problem_solved immediately for correct solutions
- One question at a time if solution needs improvement
- Stay focused on the current problem statement
- Only move to the next concept when the current one is understood
- When user expresses uncertainty, start with the smallest possible step'''
        return base_instruction + code_specific_instruction
    else:
        return base_instruction

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
        print(f"Prompt: {prompt}")
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
    elif name == "problem_solved":
        return problem_solved(**args)
    else:
        print(f"Unknown function: {name}")
        return {"error": f"Unknown function: {name}"}

def generate_welcome_message(topic, submitted_code=None, problem_statement=None, conversation_id=None):
    """Generate a personalized welcome message for a focused conversation."""
    try:
        # Format code section for context
        code_context = f"""Here's the code context we'll be working with:

```python
{submitted_code}
```""" if submitted_code else "We'll start from scratch with this topic."

        # Add problem statement context if available
        problem_context = f"\nProblem Statement:\n{problem_statement}" if problem_statement else ""

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

        system_prompt = f"""You are creating a focused welcome message for a Python learning session, using Socratic questioning to guide learning.

Context:
Topic: {topic}
Problem Statement: {problem_statement}
User's Code: {f'''```python\n{submitted_code}\n```''' if submitted_code else 'No code provided yet'}

IMPORTANT GUIDELINES FOR SOCRATIC QUESTIONING:
1. ALWAYS ask only ONE question at a time - wait for user's response before proceeding
2. NEVER provide direct solutions or obvious hints
3. Guide through discovery by asking about:
   - Their thought process
   - Why they chose certain approaches
   - What they think might happen in specific scenarios
4. When users are stuck:
   - Ask them to explain their understanding
   - Have them consider simpler versions of the problem
   - Guide them to discover patterns themselves

Question Types (Choose ONLY ONE per response):
1. Conceptual Understanding:
   - "What patterns do you notice in...?"
   - "How might this relate to...?"
   - "What assumptions are we making about...?"

2. Problem Decomposition:
   - "What smaller problems do you see within this larger one?"
   - "Which part seems most challenging to you?"
   - "What information do we need to track?"

3. Solution Design:
   - "What approaches have worked in similar situations?"
   - "How would you handle a simpler version?"
   - "What might change if we modified...?"

Your welcome message must:
1. Be professional but approachable (avoid being overly playful or formal)
2. Present the problem statement clearly, including:
   - The main problem/task to solve
   - The provided input/output examples exactly as they appear in the problem statement
   - Any constraints or requirements mentioned
3. If user provided code: Show it and acknowledge their attempt without correcting it
4. End with ONE thought-provoking question that encourages exploration
5. Keep the entire message concise (max 5-6 lines total)

Format:
1. Brief welcome with topic in **bold**
2. Problem statement with its examples:
   "Here's what we need to solve:
   **Problem:** [Problem description]
   
   **Examples:**
   ```python
   Input: [example input]
   Output: [example output]
   ```"
3. If user provided code: Show their starting point in a ```python``` code block
4. ONE focused question to guide their thinking in **bold**

Question Guidelines:
- Ask ONLY ONE question at a time and wait for response
- Never give away the solution path directly
- Ask questions that encourage pattern recognition
- Focus on understanding over implementation
- Guide users to discover relationships and concepts themselves
- Use analogies or simpler scenarios to build understanding

Remember:
- Use **bold** for emphasis on key points and questions
- Format all code and examples in ```python``` blocks
- No emojis or exclamation marks
- No direct answers or solutions
- No code corrections or improvements
- No example code if user hasn't provided any
- Do not create new examples - use only those provided in the problem statement
- Focus on guiding discovery through ONE thoughtful question at a time"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""Topic: {topic}
{problem_context}
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
        welcome_text = f"Welcome to our session on **{topic}**."
        if problem_statement:
            welcome_text += f"\n\n**Problem Statement:**\n{problem_statement}"
        if submitted_code:
            welcome_text += f"\n\n{code_context}"
        return welcome_text

def problem_solved(topic, current_problem, submitted_code, history_context=""):
    """Handle completion of a focused learning problem and suggest a harder one."""
    print("OFC: problem_solved")
    print(f"\n\n\nTopic: {topic}")
    print(f"Current Problem: {current_problem}")
    print(f"Initial Submitted Code:\n{submitted_code}")
    print(f"History Context:\n{history_context}")
    
    try:
        
        prompt = f"""Based on the following context:

Topic: {topic}

Current Problem:
{current_problem}

User's Initial Code (may contain mistakes):
```python
{submitted_code}
```

Recent Conversation Context:
{history_context}

Based on the above context and the user's demonstrated understanding, generate a harder problem that:
1. Focuses on concepts where the user showed potential misunderstandings in their initial code
2. Builds upon the successfully solved current problem
3. Introduces 1-2 new challenging aspects within the same topic area
4. Is specific and well-defined
5. Has clear requirements and constraints

Format your response as a problem statement only, without any additional explanation or notes.
Do NOT include any introductory text or congratulatory messages."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python programming challenge generator. Generate clear, specific, and well-defined problems that build upon previously solved challenges while addressing potential areas of misunderstanding."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        next_problem = response.choices[0].message.content.strip()

        # Create a new conversation with the harder problem
        result = propose_new_conversation(
            topic=topic,
            problem_statement=next_problem,
            submitted_code=""  # Start fresh for the new problem
        )

        # Add the next_challenge field to the result
        result["next_challenge"] = next_problem
        
        return result

    except Exception as e:
        print(f"Error in problem_solved: {str(e)}")
        return {
            "error": f"Failed to process problem completion: {str(e)}"
        }