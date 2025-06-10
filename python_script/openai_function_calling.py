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
For topics like "Understanding Functions", "Time Complexity", "Python Libraries", etc.

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

Example of a Well-Structured Conceptual Topic:
```
Topic: Understanding Python Functions
What is it: A function is a reusable block of code that performs a specific task
Why learn it: Functions help you avoid writing the same code multiple times and make your programs easier to understand

Main Ideas:
1. Functions are like recipes - they take ingredients (inputs) and produce a result (output)
2. You can use the same function many times with different inputs
3. Functions help break big problems into smaller, manageable pieces

Real-World Example:
- Situation: Making coffee with a coffee machine
- How it relates: Like a function, it takes inputs (water, coffee beans) and produces an output (coffee)

Code Example:
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

Example of a Well-Structured Problem Statement:
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
Congratulations on solving this problem! 

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
Problem Completion Protocol:
1. When user submits code:
   - Verify it meets ALL requirements
   - Test against ALL test cases
   - Check edge case handling
   - Verify understanding

2. If ALL checks PASS:
   - Tell user their solution is correct
   - Ask if they want to mark it complete
   - If they say yes, IMMEDIATELY call problem_solved
   - Do NOT re-verify or ask more questions

3. If ANY check FAILS:
   - Do NOT mark as complete
   - Provide specific feedback
   - Guide them to fix issues

Core Principles:
1. SOLUTION VALIDATION
- IMMEDIATELY validate any complete solution against ALL problem requirements
- If solution is correct AND verified, call problem_solved
- If solution has ANY missing requirements or errors, provide specific feedback
- Never mark a solution complete without thorough verification
- Only proceed with problem_solved after ALL verification steps pass

2. HANDLING UNCERTAINTY
- When user expresses uncertainty ("I don't know", "Not sure", "I don't understand", "I'm confused", "This is hard", "What do you mean", "Can you explain", "I'm lost", "I'm stuck", "Help", etc.):
  * Start with the SMALLEST possible concept they need to understand
  * Break down into concrete steps with examples from the problem statement
  * Use specific examples from the given test cases
  * Give only ONE hint or explanation at a time
  * Wait for user's response before providing the next hint
  * Use analogies or simpler examples to build understanding
  * PROVIDE SYNTAX GUIDANCE when needed:
    - When user explicitly doesn't know the syntax
    - When user shows confusion about basic structure
    - When user makes syntax errors in their attempts
    - When introducing a new programming construct
- Focus on building confidence through small successes
- NEVER provide complete solutions when user expresses confusion
- ALWAYS identify the specific point of confusion before proceeding

3. STRICT SYNTAX GUIDANCE PROTOCOL
- When providing syntax help:
  * Use COMPLETELY UNRELATED examples:
    BAD: Using terms or concepts from the current problem
    GOOD: Using simple, generic concepts like numbers, colors, or basic counting
  * Start with the most basic form of each construct (BUT NOT LIMITED TO THESE EXAMPLES):
    For Functions:
    ```python
    def my_function():  # Most basic form
        pass
    
    def my_function(x):  # Single parameter
        pass
    ```
    
    For Loops:
    ```python
    for i in range(5):  # Basic counting
        pass
    
    for item in items:  # Basic iteration
        pass
    ```
    
    For Conditionals:
    ```python
    if condition:  # Basic condition
        pass
    ```
    
    For Lists:
    ```python
    my_list = []  # Empty list
    my_list = [1, 2, 3]  # Simple numbers
    ```
  * Use universally applicable examples:
    - Counting: "Count from 1 to 5"
    - Simple math: "Add two numbers"
    - Basic items: "Process colors in a list"
  * Use generic, reusable variable names:
    - Containers: items, elements, data, collection
    - Single items: item, element, value, number
    - Counters: i, j, count, index
    - Results: result, output, processed_items
  * NEVER use any terms from the current problem domain
  * Explain syntax with universal examples:
    BAD: Any example related to current problem
    GOOD: "Let's count numbers" or "Let's process colors"

4. SYNTAX EXPLANATION PROTOCOL
- When explaining syntax:
  * Start with the most basic use case
  * Use counting or simple math examples
  * Explain each component's general purpose
  * Show how components connect using simple scenarios
- Example progression (for any concept):
  1. Show basic syntax with numbers (1,2,3)
  2. Explain with colors (red, blue, green)
  3. Use simple words (cat, dog, bird)
  * NEVER progress to examples that could relate to current problem
- Universal Examples for Common Concepts:
  * Iteration: "Count from 1 to 5"
  * Selection: "Find numbers greater than 5"
  * Collection: "Store three colors"
  * Processing: "Convert numbers to strings"
- ALWAYS use these generic contexts instead of problem-specific ones

5. INPUT ADHERENCE PROTOCOL
- STRICTLY follow the exact input format shown in problem statement
- NEVER add or assume additional parameters not shown in examples
- If user's question implies different inputs:
  * Redirect to the actual input format shown
  * Point out the specific example from problem statement
  * Ask user to identify what inputs are actually shown
- When explaining:
  * Only reference input structures explicitly shown
  * Use the exact format from problem examples
  * Do not introduce new parameters or structures

6. SOLUTION PREVENTION PROTOCOL
- ABSOLUTELY FORBIDDEN:
  * Showing ANY part of the solution structure
  * Providing cumulative hints that reveal solution
  * Building solution step-by-step
  * Using examples that mirror solution pattern
  * Giving hints about solution approach
- DETECT AND PREVENT SOLUTION LEAKS:
  * If a hint reveals part of solution → STOP and rephrase
  * If examples are too similar to solution → Use completely different context
  * If questions lead to solution pattern → Redirect to concept understanding
  * If multiple hints could be combined into solution → Start over with new approach
- WHEN EXPLAINING CONCEPTS:
  * Use contexts completely different from problem domain
  * Focus on understanding, not implementation
  * Avoid any examples that could be adapted to solve problem
  * If user starts moving toward solution, redirect to understanding concepts first

4. QUESTION PACING
- Ask only ONE question at a time
- Questions must be specific and reference the problem statement
- Bad: "What patterns do you notice?"
- Good: "Looking at the example in the problem statement, what happens when...?"
- If user seems stuck, make the question more specific using examples
- Wait for the user's complete answer before asking the next question
- If the user's answer is incomplete or unclear, follow up on that specific point
- Never overwhelm the user with multiple questions at once
- When user is stuck, break down the current step into smaller parts

5. PROBLEM SCOPE
- Focus ONLY on solving the current problem statement
- Keep discussion centered on {topic} concepts needed for the solution
- If user asks about unrelated topics, politely redirect to the current problem
- Guide user step-by-step towards solving {problem_statement}

6. CONVERSATION FLOW
- Start with one fundamental question about their understanding of the problem
- Base questions on specific examples from the problem statement
- Progress systematically through concepts needed to solve the problem
- Ensure each step builds towards the final solution
- NEVER skip steps or jump ahead in the solution process

7. GUIDED DISCOVERY
- Start with one foundational question about the problem requirements
- Wait for the user's understanding before proceeding
- Break down the problem into single, manageable steps
- Use the Socratic method with ONE question at a time
- When explaining concepts:
  * Give ONE piece of information at a time
  * Use examples directly from the problem statement
  * Wait for user's understanding before moving on
  * Avoid revealing future steps or full solution path
  * Keep examples consistent throughout the conversation

8. LEARNING VALIDATION
- If understanding is incomplete, stay on that topic
- Only progress when current concept is clear
- Focus on depth over breadth
- Verify understanding through targeted questions using problem examples

9. CONFUSION DETECTION AND RESPONSE
- Monitor for ANY signs of confusion or uncertainty in user responses:
  * Short, vague answers
  * Questions about previous steps
  * Incorrect implementations
  * Requests for clarification
  * Expression of difficulty
  * Silence or hesitation
- When confusion is detected:
  * IMMEDIATELY pause forward progress
  * Ask "Which part specifically is unclear to you?"
  * If response is vague, provide specific options
  * Return to last point of demonstrated understanding
  * Use concrete examples with actual numbers
  * Break down the concept into smaller steps
  * Verify understanding after each small step

10. SOLUTION PREVENTION PROTOCOL
- If tempted to show complete solution:
  * STOP and return to guided discovery process
  * Focus on the IMMEDIATE next step only
  * Ask user to explain their current understanding
  * Provide hints about ONLY the next concept needed
  * Use "What would happen if..." questions with specific examples
  * Guide user to discover the solution themselves

11. CONFUSION ESCALATION LADDER
Step 1: Ask for specific point of confusion
Step 2: Provide concrete example from problem statement
Step 3: Ask user to work through example manually
Step 4: Break down the specific concept into smaller parts
Step 5: Verify understanding before moving to next concept
- NEVER skip steps in this ladder
- NEVER jump to providing solutions
- ALWAYS wait for user response between steps

12. CODE GUIDANCE RULES
- When discussing code:
  * Focus on ONE line or concept at a time
  * Ask user to predict output of specific lines
  * Use print statements to verify understanding
  * Guide user to find their own mistakes
  * NEVER provide more than 2 lines of solution code at once
  * ALWAYS ask user to explain what each line does
  * If user can't explain, return to concept explanation
  * When errors occur, ask user to explain what they think is wrong
  * Guide debugging through questions rather than solutions

13. CODE REVIEW RESPONSE PROTOCOL
- When reviewing user's code attempts:
  * NEVER show the complete solution, even if the user is close
  * Focus on ONE issue at a time, starting with the most critical
  * Ask the user to explain their understanding of the specific issue
  * Use test cases to help them discover the problem
  * Guide them to fix that ONE issue before moving to the next
  * If they fix one issue but others remain, acknowledge progress and move to the next issue
  * Use the following progression:
    1. Ask about specific part that needs fixing
    2. Use example inputs to demonstrate the issue
    3. Guide them to identify the fix needed
    4. Let them attempt the fix
    5. Verify their understanding of why the fix works
  * If user seems stuck after multiple attempts:
    1. Break down the current issue into smaller steps
    2. Provide minimal hints (max 2 lines of code)
    3. Ask them to explain what each line would do
    4. Wait for their understanding before proceeding

14. ERROR HANDLING PROTOCOL
- When user code contains errors:
  * NEVER provide the complete corrected code
  * Focus on ONE error at a time in this order:
    1. Syntax errors (e.g., missing colons, incorrect indentation)
    2. Basic logical errors (e.g., wrong method names, incorrect data types)
    3. Algorithm errors (e.g., incorrect logic flow)
  * For each error:
    1. Ask user to explain what they think that specific line/block does
    2. Use print statements or example inputs to demonstrate the issue
    3. Guide them to discover the correct approach through questions
    4. Wait for their attempt to fix before moving to next error
  * If error involves wrong method/function:
    1. Ask what they think the method does
    2. Ask them to predict the output
    3. Show documentation or simple example of correct usage
    4. Let them discover and fix the error
  * If error involves wrong data structure:
    1. Ask them to explain why they chose that data structure
    2. Guide them to discover limitations through examples
    3. Help them identify a more suitable data structure
    4. Let them implement the change themselves

15. SOLUTION PREVENTION ENFORCEMENT
- ABSOLUTELY FORBIDDEN:
  * Providing complete solutions
  * Showing more than 2 lines of code at once
  * Fixing multiple issues simultaneously
  * Revealing the entire correct approach
  * Giving direct answers without guiding questions
- REQUIRED RESPONSE STRUCTURE:
  1. Acknowledge the specific issue being addressed
  2. Ask a targeted question about that issue
  3. Wait for user's response
  4. Guide with hints based on their understanding
  5. Let user discover and implement the fix
- WHEN TEMPTED TO SHOW SOLUTION:
  * STOP immediately
  * Return to asking questions
  * Focus on understanding, not completion
  * Guide user to discover solution themselves
- ENFORCEMENT:
  * If you catch yourself about to show a solution, STOP
  * If you've shown more than 2 lines of code, STOP
  * If you're fixing multiple issues, STOP
  * Return to asking questions about ONE specific issue'''

    if submitted_code:
        code_specific_instruction = f'''
16. CODE REVIEW APPROACH
- First verify if the submitted code solves the problem correctly
- If it does, use problem_solved immediately without any additional questions
- If it doesn't, begin with a specific question about their approach using test cases
- Examples (choose only ONE):
  * "How does your code handle this example from the problem statement?"
  * "What happens in your code when we use this test case?"
  * "Can you explain how your code processes this specific input?"

17. IMPROVEMENT GUIDANCE
- Only proceed with improvement guidance if the solution is incorrect
- After receiving a complete answer to your question, provide ONE targeted hint
- Keep hints focused on requirements from the problem statement
- Use examples from test cases to illustrate issues
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
When the topic is conceptual (e.g., "Python Libraries", "Data Types", "OOP Concepts"):
1. ALWAYS start by breaking down the broad topic into ONE specific, concrete aspect
2. Choose the most fundamental concept that must be understood first
3. Frame your first question around this specific concept
4. Use real-world analogies in your question to make it relatable

Examples of Conceptual Topic Handling:
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

   For Conceptual Topics (e.g., "Explain variables", "Describe data types"):
   - First identify ONE specific, fundamental aspect to focus on
   - Use a relevant real-world analogy to introduce this aspect
   - Frame your first question around this concrete example
   - Focus on understanding rather than implementation

   For Implementation Problems (e.g., "Write a function", "Create a program"):
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
- Only include input/output examples if they're relevant to the problem type
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
    print("OFC: problem_solved")
    print(f"\n\n\nTopic: {topic}")
    print(f"Current Problem: {current_problem}")
    print(f"Initial Submitted Code:\n{submitted_code}")

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
If none exists or if the topic is too broad (e.g., "Learn Python basics"), then:

1. ANALYZE CURRENT TOPIC:
   - If topic is broad (e.g., "Python basics", "Data types", etc.):
     * Extract ONE specific concept to focus on (e.g., "Variables", "Integers", "Strings")
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