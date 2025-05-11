import json
import openai
import jsonify

functions = [{
        "type": "function",
        "function": {
            "name": "propose_new_conversation",
            "description": "Suggests starting a focused conversation when a deep or complex topic is detected.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic or exercise to focus on. For example, 'For Loop in Python (beginner)', 'Two Sum', 'Roman to Integer', 'Sudoku Solver'"
                    }
                },
                "required": ["topic"]
            }
        
        }
}]

propose_template = """\
Briefly talk about {topic}, and tell the user if they're interested in this topic, please click the "Create new chat" button to start a new conversation and go deeper into it.
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

    # return f"Starting a new conversation about: {topic}"


def call_function(name, args_str):
    args = json.loads(args_str)
    print(args)
    if name == "propose_new_conversation":
        return propose_new_conversation(**args)