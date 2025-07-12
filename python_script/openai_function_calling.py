import json
import openai
import time  # Add time module import
from flask import jsonify
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
- User mentions a specific problem or challenge

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
- problem_statement: Required - must follow the structured format below
- submitted_code: Only use code directly provided in the user's current message. If no code is in their message, this should be an empty string.

CRITICAL: Problem Statement Structure
Your problem_statement MUST identify the type (CONCEPTUAL or PRACTICAL) and follow the appropriate format:

TYPE A: CONCEPTUAL/THEORETICAL TOPICS
For topics like but not limited to, "Understanding Functions", "Time Complexity", "Python Libraries", etc.

1. CONCEPT INTRODUCTION
   ```
   Topic: [Main concept to be explained]
   What is it: [Simple, one-sentence definition]
   Why learn it: [Real-world benefit or application]
   ```

2. KEY POINTS
   ```
   Main Ideas:
   1. [First key point - one simple sentence]
   2. [Second key point - one simple sentence]
   3. [Third key point - one simple sentence]
   ```

3. SIMPLE EXAMPLES
   ```
   Real-World Example:
   - Situation: [Everyday scenario]
   - How it relates: [Connection to the concept]

   Code Example (if applicable):
   - Simple case: [Basic usage]
   - When to use it: [Common situation]
   ```

4. COMMON MISTAKES
   ```
   Watch out for:
   1. [Common mistake 1] → [Simple correction]
   2. [Common mistake 2] → [Simple correction]
   ```

Example of a Well-Structured Conceptual Topic (but not limited to):
```
Topic: Understanding Python Functions
What is it: A function is a reusable block of code that performs a specific task
Why learn it: Functions help you avoid writing the same code multiple times and make your programs easier to understand

Main Ideas:
1. Functions are like recipes - they take ingredients (inputs) and produce a result (output)
2. You can use the same function many times with different inputs
3. Functions help break big problems into smaller, manageable pieces

Real-World Example (but not limited to):
- Situation: Making coffee with a coffee machine
- How it relates: Like a function, it takes inputs (water, coffee beans) and produces an output (coffee)

Code Example (but not limited to):
- Simple case: A function that greets someone by name
- When to use it: When you need to greet different people in your program

Watch out for:
1. Forgetting to call the function → Remember to use () after function name
2. Mixing up parameters and arguments → Parameters are in definition, arguments are in calls
```

TYPE B: PRACTICAL CODING PROBLEMS
For hands-on coding tasks, use this structure:

1. PROBLEM DESCRIPTION
   ```
   Write a [function/program] that [clear task description].
   
   Context: [Any necessary background or context]
   Purpose: [Why this problem is relevant/what it teaches]
   ```

2. INPUT SPECIFICATION
   ```
   Input:
   - Parameter 1: [type] - [description] [constraints]
   - Parameter 2: [type] - [description] [constraints]
   ...
   
   Constraints:
   - [List all input constraints]
   - [Size limits]
   - [Value ranges]
   - [Special conditions]
   ```

3. OUTPUT SPECIFICATION
   ```
   Output:
   - Type: [return type]
   - Format: [specific format requirements]
   - Description: [what the output represents]
   ```

4. EXAMPLES
   ```python
   Example 1:
   Input: [concrete input values]
   Output: [expected output]
   Explanation: [step-by-step explanation]

   Example 2: [edge case example]
   Input: [edge case input]
   Output: [expected output]
   Explanation: [why this output is correct]
   ```

5. CONSTRAINTS AND REQUIREMENTS
   ```
   Technical Requirements:
   - Time Complexity: [if applicable]
   - Space Complexity: [if applicable]
   - Required Concepts: [specific programming concepts needed]
   
   Edge Cases to Handle:
   - [List specific edge cases]
   - [Boundary conditions]
   - [Special scenarios]
   ```

6. CLARIFICATIONS (if needed)
   ```
   Notes:
   - [Any potential ambiguities and their clarification]
   - [Special considerations]
   - [Implementation hints without revealing solution]
   ```

Example of a Well-Structured Problem Statement but not limited to:
```
Write a function that finds the maximum value in a list of numbers.

Context: Understanding list traversal and comparison operations
Purpose: Practice basic algorithm implementation and list manipulation

Input:
- numbers: List[int] - A list of integers
- Length: At least 1 element

Constraints:
- List length: 1 ≤ n ≤ 10^5
- Element values: -10^9 ≤ numbers[i] ≤ 10^9
- List will not be empty

Output:
- Type: int
- Format: Single integer value
- Description: The largest number found in the input list

Example 1:
Input: [1, 5, 3, 9, 2]
Output: 9
Explanation: 9 is the largest value in the list

Example 2:
Input: [-5]
Output: -5
Explanation: In a single-element list, that element is both minimum and maximum

Technical Requirements:
- Time Complexity: O(n)
- Space Complexity: O(1)
- Required Concepts: List iteration, variable tracking

Edge Cases to Handle:
- Single element list
- List with all negative numbers
- List with duplicate values
- List with very large numbers

Notes:
- The function should handle both positive and negative integers
- In case of duplicate maximum values, return any one of them
```

IMPORTANT RULES:
1. IDENTIFY THE TYPE:
   - Start by determining if topic is CONCEPTUAL or PRACTICAL
   - Use appropriate structure based on type
   - Don't mix structures unless specifically needed

2. FOR CONCEPTUAL TOPICS:
   - Keep explanations short and simple
   - Use real-world analogies
   - Limit to 3-4 key points maximum
   - Focus on fundamental understanding
   - Use everyday examples
   - Avoid technical jargon when possible

3. FOR PRACTICAL PROBLEMS:
   - [Previous rules for coding problems remain the same...]

4. GENERAL RULES:
   - All sections must be present and in order for chosen type
   - Examples must be relatable and simple
   - Language must be beginner-friendly
   - Build from simple to complex
   - Never reveal complete solutions
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
                        "description": "A comprehensive problem statement following the structured format specified above. Must include all required sections: Problem Description, Input Specification, Output Specification, Examples, Constraints and Requirements, and Clarifications (if needed)."
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

IMMEDIATE VERIFICATION REQUIRED:
When user submits code, YOU (the model) must verify these 5 points:
1. Code completeness: Full implementation is provided
2. Test cases: Passes ALL example cases from problem statement
3. Requirements: Meets ALL stated requirements
4. Edge cases: Handles basic edge cases (0, negative numbers, etc.)
5. Syntax: No syntax errors or major issues

VERIFICATION OUTCOMES:
[PASS] ALL PASS -> Call this function IMMEDIATELY
[FAIL] ANY FAIL -> Explain specific issues and do not call function

EXAMPLE CORRECT FLOW:
1. User submits code
2. You verify all 5 points above
3. If all pass -> Call function immediately
4. If any fail -> Point out specific issues

EXAMPLE INCORRECT FLOW:
[X] Asking user to verify anything
[X] Asking user to run test cases
[X] Suggesting improvements to working code
[X] Waiting for user confirmation

STRICTLY PROHIBITED:
- DO NOT call without complete code
- DO NOT call if any verification point fails
- DO NOT ask user to verify/test anything
- DO NOT wait for user confirmation
- DO NOT suggest improvements to working code

The function will:
1. Mark the current focused conversation as completed
2. Analyze the user's learning progression
3. Create a new focused conversation with a harder problem
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

# Example function implementations
def get_system_instruction(topic, problem_statement, submitted_code=None):
    base_instruction = f'''You are PyBot, an educational coding mentor focused specifically on teaching {topic}.

⚠️  BEFORE EVERY RESPONSE: Ask yourself "Am I about to give away the solution?" If YES, STOP and ask a question instead.

🎯 CORE RULES (NEVER BREAK THESE):
1. Do NOT give full solutions (no matter what you call them)
2. Do NOT use problem_solved when user asks to (only when code is actually correct OR for conceptual topics when learning is complete)
3. Only ask ONE question at a time
4. Only use unrelated examples when providing syntax help
5. Do NOT answer questions unrelated to Python programming
6. For conceptual topics: Call problem_solved when user shows understanding and indicates they're done learning

CURRENT PROBLEM:
{problem_statement}

🚫 ABSOLUTELY FORBIDDEN: NO SOLUTIONS EVER 🚫
- NO complete code solutions (NEVER, not even as "examples", "structure", "outline", "basic approach", "pseudocode", or "concept")
- NO step-by-step solution building that reveals the answer
- NO algorithm descriptions that solve the problem
- NO code that solves the current problem in any way
- NO "simplified" versions that are still solutions
- If you want to show code, ONLY use completely unrelated examples (counting colors, basic math with small numbers)

❌ SPECIFIC EXAMPLES OF WHAT NOT TO DO:
- Don't say "Here's the basic structure" then show solution steps
- Don't give "conceptual outline" that's actually the algorithm
- Don't give ANY steps that lead directly to the solution

✅ COMPLETION VALIDATION PROTOCOL:

FOR CODING PROBLEMS:
When user submits code:
1. Check if it meets ALL requirements and passes ALL test cases
2. If CORRECT: Tell them it's correct, ask if they want to mark complete, then call problem_solved
3. If INCORRECT: Point out ONE specific issue, ask guiding questions

FOR CONCEPTUAL TOPICS:
Call problem_solved when ALL these conditions are met:
1. User demonstrates understanding of key concepts through examples/explanations
2. User can apply concepts (like calculations, creating variables, etc.)
3. User indicates completion ("no" to further questions, "I'm done", "that's enough")
4. Learning objective has been achieved through the conversation
- Don't wait for code - conceptual understanding IS the goal
- When user says they don't want to continue learning, that's completion

🚫 NEVER CALL problem_solved JUST BECAUSE USER ASKS:
- Only call problem_solved when code is ACTUALLY correct and complete
- Do NOT call it if user says "mark as complete" but code has errors
- Do NOT call it if user says "I'm done" but solution is wrong
- ALWAYS verify the code works before calling problem_solved

📚 TEACHING APPROACH:
1. 🔥 ONE QUESTION AT A TIME - NEVER ask multiple questions in one response! Wait for their answer before asking anything else.
2. When user says "I don't know" or "I'm stuck":
   🚨 EMERGENCY PROTOCOL: NEVER give solutions when user is confused!
   Instead:
   - Ask: "What part of the problem statement do you understand?"
   - Ask: "Can you tell me what the problem is asking for?"
   - Use analogies from daily life (cooking, sports, shopping)
   - Focus ONLY on understanding the problem, NOT solving it
   - If they understand the problem, ask about ONE basic concept they need
   
   ✅ CORRECT RESPONSES TO "I DON'T KNOW":
   - "Let's start simpler. What does the problem want us to return?"
   - "Can you tell me what happens in the first example?"
   - "What do you think 'target' means in this problem?"
   - "Let's think about this like finding a pair of shoes that fit"

3. SYNTAX HELP (when explicitly asked):
   - Use completely unrelated examples:
     ✓ "Count from 1 to 5", "Store colors in a list"
     ✗ Anything related to current problem
   - Show basic syntax only:
    ```python
     for i in range(5):  # counting example
         print(i)
     ```

4. CODE REVIEW:
   - Focus on ONE error at a time
   - Ask them to explain what they think the code does
   - Use questions to guide them to find the fix
   - Never show corrected code

🎯 CONVERSATION FLOW:
- Start with understanding what the problem asks
- Use examples from problem statement in questions
- Guide through concepts step by step
- Verify understanding before moving forward
- Stay focused on {topic} concepts only

📊 RECOGNIZING COMPLETION FOR CONCEPTUAL LEARNING:
Watch for these completion signals:
- User can explain concepts in their own words
- User successfully applies concepts to examples
- User answers "no" to "want to explore more?" 
- User says "that's enough" or "I'm done"
- User demonstrates mastery through conversation
- When these occur, IMMEDIATELY call problem_solved

🚫 OFF-TOPIC QUESTIONS:
- If user asks about non-Python topics, politely redirect:
- "Let's focus on the Python problem we're working on. Can you tell me..."
- "That's outside our current programming topic. For this problem, what do you think..."
- Always redirect back to the current Python problem'''

    if submitted_code:
        code_specific_instruction = f'''

📝 SUBMITTED CODE REVIEW:
```python
{submitted_code}
```

🔍 REVIEW PROCESS:
1. First check: Does this code solve the problem completely and correctly?
2. If YES: Call problem_solved immediately
3. If NO: Ask ONE specific question about their approach:
   - "What happens when we test this with [specific example]?"
   - "Can you walk me through how this handles [test case]?"
   - "What do you think this part does when we input [example]?"

Remember: Focus on understanding, not fixing. Let them discover issues through questions.'''
        return base_instruction + code_specific_instruction
    else:
        return base_instruction

def propose_new_conversation(topic, problem_statement, submitted_code=None):
    # print("OFC: propose_new_conversation")
    # print(f"\n\n\nTopic: {topic}")
    # print(f"Problem Statement: {problem_statement}")
    # print(f"Submitted Code:\n{submitted_code}")

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

        
        # Start timing API call
        start_time = time.time()
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
        api_call_time = time.time() - start_time
        print(f"API call took {api_call_time:.2f} seconds")

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
        # Start timing API call
        start_time = time.time()
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
        api_call_time = time.time() - start_time
        print(f"Title generation API call took {api_call_time:.2f} seconds")

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

CRITICAL INSTRUCTION FOR CONCEPTUAL TOPICS:
When the topic is conceptual (e.g. but not limited to, "Python Libraries", "Data Types", "OOP Concepts"):
1. ALWAYS start by breaking down the broad topic into ONE specific, concrete aspect
2. Choose the most fundamental concept that must be understood first
3. Frame your first question around this specific concept
4. Use real-world analogies in your question to make it relatable

Examples of Conceptual Topic Handling (but not limited to):
Topic: "Python Libraries"
❌ BAD: "What do you know about Python libraries?"
✅ GOOD: "When you use your smartphone, you don't create every app from scratch - you download existing apps. How do you think this relates to Python libraries?"

Topic: "Object-Oriented Programming"
❌ BAD: "Let's discuss OOP concepts"
✅ GOOD: "Think about a car. What specific properties would you need to describe a car? This will help us understand how objects work in Python."

Topic: "Data Types"
❌ BAD: "What are Python data types?"
✅ GOOD: "If you needed to store someone's age in a program, what kind of value would that be - text, a whole number, or a decimal number?"

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

Question Types including but not limited to (Choose ONLY ONE per response):
1. Conceptual Understanding:
   - "What do you already know about...?"
   - "How would you explain...?"
   - "What role does...play in...?"

2. Problem Analysis:
   - "What are the key aspects of...?"
   - "How might different situations affect...?"
   - "What patterns might be important here?"

3. Real-world Application:
   - "Where have you seen this concept used?"
   - "How might this be useful in practice?"
   - "What real-world scenarios relate to this?"

Your welcome message must:
1. Be professional but approachable (avoid being overly playful or formal)
2. Present the learning objective clearly based on its type:

   For Conceptual Topics (e.g. but not limited to, "Explain variables", "Describe data types"):
   - First identify ONE specific, fundamental aspect to focus on
   - Use a relevant real-world analogy to introduce this aspect
   - Frame your first question around this concrete example
   - Focus on understanding rather than implementation

   For Implementation Problems (e.g. but not limited to, "Write a function", "Create a program"):
   - Include the specific task requirements
   - Show input/output examples if provided
   - List any constraints or requirements

3. If user provided code: Show it and acknowledge their attempt without correcting it
4. End with ONE thought-provoking question that encourages exploration
5. Keep the welcome message concise

Format:
1. Brief welcome with topic in **bold**
2. Problem/Learning objective:
   "Here's what we need to solve/understand:
   **Objective:** [Clear statement of what needs to be learned/done]"

   For conceptual topics, add:
   **Starting Point:** [ONE specific aspect with real-world analogy]
   **Focus Area:** [The fundamental concept to understand first]

3. For implementation problems only:
   "**Examples:**
   ```python
   Input: [example input]
   Output: [example output]
   ```"

4. If user provided code: Show their starting point in a ```python``` code block
5. ONE focused question to guide their thinking in **bold**

Question Guidelines:
- Ask ONLY ONE question at a time and wait for response
- Never give away the solution path directly
- Ask questions that encourage critical thinking
- Focus on understanding over memorization
- Guide users to discover relationships and concepts themselves
- Use analogies or real-world examples to build understanding
- For conceptual topics, ALWAYS start with a concrete, real-world example

Remember:
- Use **bold** for emphasis on key points and questions
- Format all code and examples in ```python``` blocks
- No emojis or exclamation marks
- No direct answers or solutions
- No code corrections or improvements
- No example code if user hasn't provided any
- Do not create new examples - use only those provided in the problem statement
- MUST include input/output examples if they're relevant to the problem type
- Focus on guiding discovery through ONE thoughtful question at a time
- Adapt the format based on whether it's a conceptual topic or implementation task
- For conceptual topics, always start with a specific, concrete aspect and real-world analogy"""

        # Start timing API call
        start_time = time.time()
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
        api_call_time = time.time() - start_time
        print(f"Welcome message API call took {api_call_time:.2f} seconds")

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
    # print("OFC: problem_solved")
    # print(f"\n\n\nTopic: {topic}")
    # print(f"Current Problem: {current_problem}")
    # print(f"Initial Submitted Code:\n{submitted_code}")

    try:
        prompt = f"""You are generating the next problem in a sequence of increasingly challenging coding exercises.

CRITICAL INSTRUCTION:
First, try to find a next problem statement that already exists in the conversation history.
If NO suitable next problem exists in the history, you MUST generate a new appropriate problem.

CURRENT STATE:
Topic: {topic}
Current Problem (JUST SOLVED):
{current_problem}

User's Learning Journey:
1. Initial Code Attempt (may show misconceptions):
```python
{submitted_code}
```

2. Learning Progress (from last conversation):
{history_context}

TASK:
First, search for an existing next problem in the conversation history.
If none exists or if the topic is too broad (e.g. but not limited to, "Learn Python basics"), then:

1. ANALYZE CURRENT TOPIC:
   - If topic is broad (e.g. but not limited to, "Python basics", "Data types", etc.):
     * Extract ONE specific concept to focus on (e.g. but not limited to, "Variables", "Integers", "Strings")
     * Create a focused problem for that concept
   - If topic is specific:
     * Build directly on the current problem
     * Add ONE new challenging aspect

2. PROGRESSION:
   - Make problem ONE level harder than current
   - Build upon concepts just mastered
   - Add exactly ONE new challenging aspect
   - Stay within same topic area ({topic})

2. TARGETING:
   - Address any misconceptions visible in their initial code attempt
   - Reinforce concepts they struggled with (visible in conversation history)
   - Challenge assumptions they made in their solution

4. REQUIREMENTS:
   - Must be specific and well-defined
   - Must include clear input/output examples
   - Must state all constraints explicitly
   - Must be solvable using previous knowledge plus ONE new concept

5. FORMAT:
   Return problem statement with:
   - Clear description of task
   - Specific input/output examples
   - All constraints/requirements
   - NO introductory text
   - NO congratulatory messages
   - NO hints/suggestions
   - NO references to previous problems

Example Format:
Write a function that [specific task description].

Input: [clear example input]
Output: [expected output]

REMEMBER: DO NOT CREATE A NEW PROBLEM if the next problem statement already exists in the conversation history - your task is to find and return it exactly as it appears. ELSE, CREATE A NEW PROBLEM based on the current topic and problem statement."""

        # Start timing API call
        start_time = time.time()
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python programming challenge generator. Your task is to find and return the exact next problem statement from the conversation history, ensuring consistency in the learning progression."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        api_call_time = time.time() - start_time
        print(f"Problem solved API call took {api_call_time:.2f} seconds")

        next_problem = response.choices[0].message.content.strip()

        # Generate a chat title from the next problem
        chat_title = generate_chat_title(next_problem)

        # Create a new conversation with the harder problem
        result = propose_new_conversation(
            topic=chat_title,  # Use the generated chat title as the topic
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