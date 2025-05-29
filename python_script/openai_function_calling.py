import json
import openai
import jsonify

# Function definitions for OpenAI function calling
functions = [
    {
        "type": "function",
        "function": {
            "name": "propose_new_conversation",
            "description": 
'''
Use this function whenever the user's message includes, directly or indirectly, a question, statement, or request that can be interpreted as a coding challenge, algorithmic exercise, or programming problem statement—regardless of how the user phrases it.
Common trigger phrases include:

"Write a function that..."

"How do you solve...?"

"Given an array/string/list..."

"Return the result of..."

"What is the algorithm for..."

"Find the output when..."

"Implement..."

Any request to code a solution for a problem.
This includes both classic coding interview problems (e.g., 'Two Sum', 'Palindrome Checker', 'Binary Tree Traversal'), practical programming questions (e.g., 'How do I parse a CSV file in Python?'), and any mathematical, logical, or algorithmic scenario that requires a solution.
Do not trigger for purely conceptual, theoretical, or general questions that do not request code or an explicit algorithm.
''',
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic/exercise/problem to focus on. For example, 'For Loop in Python (beginner)', 'Two Sum', 'Roman to Integer', 'Sudoku Solver'"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_problem_solved",
            "description": "Use this function ONLY when the user has successfully solved the current problem in a focused conversation. This will mark the problem as completed and propose a new, more challenging problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "The ID of the current conversation"
                    },
                    "next_challenge": {
                        "type": "string",
                        "description": "A proposal for a new, slightly more challenging problem related to the one just solved. Be specific about the problem."
                    }
                },
                "required": ["next_challenge"]
            }
        }
    }
]

# Template for proposing a new conversation
propose_template = """\
I see you're asking about {topic}. This appears to be a specific programming challenge that we can explore in depth.

Would you like to focus on solving this specific problem step by step? I can guide you through the process of understanding and implementing a solution.
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
def propose_new_conversation(topic):
    print("OFC: propose_new_conversation")
    print("\n\n\n"+topic)
    try:
        prompt = propose_template.format(topic=topic)

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.3,
        )

        gpt_response = response.choices[0].message.content

        return {"topic": topic, "gpt_response": gpt_response, "invite": True}
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "error": "Failed to get response from OpenAI. Please check the API key."
        }), 500

def mark_problem_solved(conversation_id=None, next_challenge=None):
    print("OFC: mark_problem_solved")
    print(f"\n\n\nNext challenge: {next_challenge}")
    try:
        # Format the response using the template
        gpt_response = next_challenge_template.format(next_challenge=next_challenge)
        
        # In a real implementation, you would make a call to mark the conversation as completed
        # This is now handled in the main.py file with the /mark-conversation-complete endpoint
        
        return {"next_challenge": next_challenge, "gpt_response": gpt_response, "invite": True}
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
    elif name == "mark_problem_solved":
        return mark_problem_solved(**args)
    else:
        print(f"Unknown function: {name}")
        return {"error": f"Unknown function: {name}"}