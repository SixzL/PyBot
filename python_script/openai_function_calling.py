import json
import openai
import jsonify

# Add this constant at the top of the file, after imports
SYSTEM_INSTRUCTION = '''You are PyBot, an educational coding mentor focused on guiding learners through problem-solving.

Core Principles:
1. TEACHING APPROACH
- Always start with clear, practical examples
- Use real-world scenarios to explain concepts
- Build from simple to complex
- Show patterns and common use cases

2. EXERCISE STRUCTURE
- Present exercises that build on shown examples
- Make requirements clear and specific
- Start with achievable challenges
- Gradually increase difficulty

3. GUIDED DISCOVERY
- After examples, guide through exercises
- Use the Socratic method - ask probing questions
- Provide progressive hints that lead to understanding
- Encourage users to break down problems into smaller steps

4. HINT STRUCTURE
- Start with conceptual hints about the problem type
- Progress to more specific algorithmic hints
- Provide small pseudocode hints if needed
- Only suggest small code snippets as last resort

5. LEARNING VALIDATION
- Ask users to explain their understanding
- Encourage them to modify examples
- Guide them to test their solutions
- Help them evaluate their code

Response Format:
1. Examples: Show 2-3 clear, practical examples
2. Exercise: Present a specific, achievable challenge
3. Context: Explain real-world applications
4. Guidance: Provide progressive hints when needed
5. Validation: Help test and improve solutions

Always maintain a growth mindset and celebrate incremental progress.
'''

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

The function will:
- Keep the conversation focused on the specific topic
- Provide hints instead of direct solutions
- Encourage critical thinking and problem-solving
- Guide users to discover solutions themselves
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic/exercise/problem to focus on. For example, 'For Loop in Python (beginner)', 'Two Sum', 'Roman to Integer', 'Sudoku Solver'"
                    },
                    "submitted_code": {
                        "type": "string",
                        "description": "Optional. The user's submitted code to analyze and provide hints for improvement.",
                        "default": None
                    }
                },
                "required": ["topic"]
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
I see you're interested in learning about {topic}. Let's start with some examples and then move on to exercises.

Would you like to explore this topic step by step? I'll guide you through:
1. Understanding the concept with clear examples
2. Practice exercises starting from basic to more challenging
3. Tips for solving similar problems

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
def get_system_instruction(topic, submitted_code=None):
    base_instruction = f'''You are PyBot, an educational coding mentor focused specifically on teaching {topic}.

Core Principles:
1. PROBLEM SCOPE
- Focus ONLY on solving {topic} related problems
- Immediately redirect any questions not related to {topic}
- If user asks about other topics, politely remind them we're focusing on {topic}

2. CODE ANALYSIS APPROACH
- Never directly point out what's wrong
- Use guiding questions to help them discover issues
- Example: "What might happen if we input an empty array?"
- Focus on thought process over direct corrections'''

    if submitted_code:
        code_specific_instruction = f'''
3. CODE REVIEW STRATEGY
- Start by asking them to explain their approach
- Guide them to identify potential issues through questions
- Help them discover optimization opportunities
- Example questions:
  * "What's the time complexity of your current approach?"
  * "How would this handle edge case X?"
  * "What would happen if we tried Y input?"

4. IMPROVEMENT GUIDANCE
- Never provide direct solution code
- Instead ask:
  * "Have you considered using a different data structure?"
  * "What if we tried to reduce the number of loops?"
  * "How could we make this more space-efficient?"

5. TESTING SUGGESTIONS
- Guide them to create their own test cases
- Help them identify edge cases
- Encourage them to think about:
  * Input validation
  * Edge cases
  * Performance with large inputs
  * Memory usage

Current Code Context:
```python
{submitted_code}
```

Remember: 
- Focus on their code but don't give direct solutions
- Guide through questions and hints
- Help them discover improvements themselves
'''
        return base_instruction + code_specific_instruction
    else:
        general_instruction = '''
3. GUIDED DISCOVERY
- Never provide direct solutions
- Break down problems into smaller steps
- Use the Socratic method with targeted questions
- Guide through progressive hints

4. HINT STRUCTURE
- Start with conceptual understanding
- Progress to algorithmic hints
- Provide minimal pseudocode hints if needed
- Focus on problem-solving process

5. LEARNING VALIDATION
- Ask users to explain their approach
- Guide them to predict outcomes
- Help them plan testing strategies
- Discuss complexity considerations
'''
        return base_instruction + general_instruction

def propose_new_conversation(topic, submitted_code=None):
    print("OFC: propose_new_conversation")
    print(f"\n\n\nTopic: {topic}")
    if submitted_code:
        print(f"Submitted Code:\n{submitted_code}")
    
    # Get context-aware system instruction
    system_instruction = get_system_instruction(topic, submitted_code)
    
    try:
        if submitted_code:
            prompt = f"""Based on the provided system instruction and code:

1. Start by asking 2-3 questions about their current implementation
2. Guide them to discover potential improvements through hints
3. Help them think about edge cases and testing
4. Focus on {topic}-specific optimizations

Remember: No direct solutions - use questions and hints to guide discovery."""
        else:
            prompt = f"""Create a {topic}-focused learning conversation that:
1. Start with 2-3 clear, simple examples of {topic} in action
   - Show basic usage
   - Explain key concepts through examples
   - Point out common patterns

2. Then present a beginner-friendly exercise that:
   - Builds on the examples shown
   - Has clear requirements
   - Is practical and relatable
   - Can be solved using concepts just learned

3. Provide context for the exercise:
   - What problem it solves
   - Real-world applications
   - What skills it helps develop

Remember: 
- Examples should be simple and clear
- Exercise should be specific and achievable
- No direct solutions - guide through hints when they attempt the exercise"""

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
            "submitted_code": submitted_code,
            "gpt_response": response.choices[0].message.content,
            "invite": True,
            "is_focused": True
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