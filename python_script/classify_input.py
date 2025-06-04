import openai
import textwrap
import os
from dotenv import load_dotenv
""" 
5. algorithm_design: The user is asking for help designing or implementing an algorithm.
6. optimization: The user is asking for help optimizing Python code.
7. data_structures: The user is asking for help with data structures.
8. error_handling: The user is asking for help handling exceptions or errors.
9. testing: The user is asking for help writing or debugging unit tests.
10. deployment: The user is asking for help deploying Python applications.
11. data_science: The user is asking for help with data science or machine learning tasks.
12. web_scraping: The user is asking for help with web scraping.
13. file_handling: The user is asking for help reading or writing files.
14. concurrency: The user is asking for help with multi-threading or multi-processing.
15. api_integration: The user is asking for help integrating with external APIs.
16. code_review: The user is asking for feedback on their Python code.
"""

classification_prompt =textwrap.dedent("""\
            You are an intent classification system for a Python programming assistant. Your task is to classify the user's input into one of the following categories:
            
            1. code_generation: The user is asking for Python code to solve a specific task.
            2. explanation: The user is asking for an explanation of a Python concept or code snippet.
            3. debugging: The user is asking for help fixing an error or bug in their code.
            4. library_help: The user is asking for help with a specific Python library.
            5. bot_identity: The user is asking about the chatbot itself, such as "Who are you?" or "What can you do?".
            6. unknown: The user's intent is unclear or does not fit into the above categories.

            Respond with only the category name that best matches the user's input.

            User Input: {user_input}
            Category:
""")
# Load .env from the parent directory
dotenv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '.env')
load_dotenv(dotenv_path)

client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

def classify_input(messages):
    response = client.chat.completions.create(
        messages=messages,
        model="gpt-4o-mini",
    )
    return response.choices[0].message.content

def select_metaprompt(type):
    if type == "code_generation":
        return  textwrap.dedent("""\
                    Refine the following prompt to ensure that the chatbot guides the user through structured problem-solving in Python.  
                    The refined prompt should be designed for a **chatbot to respond appropriately to the user's problem**, rather than simply describing how to assist.  

                    The refined prompt should:  
                    - Clearly instruct the chatbot to **define the problem statement based on the user's task**.  
                    - Guide the chatbot to outline key constraints and expected inputs/outputs **for the user's specific problem**.  
                    - Ensure the chatbot encourages the user to think about edge cases and possible optimizations **for the given problem**.  
                    - Direct the chatbot to provide a **hint tailored to the user's specific problem**, ensuring the chatbot does not just describe problem-solving techniques in general.  
                    - Ensure the chatbot **does not provide the complete solution**, but **only gives a hint for the first step**.  

                    **The refined prompt must integrate the user's specific programming task into the instructions.**  

                    {user_input}

                    Only return the refined prompt.
        """)
    elif type == "explanation":
        return  textwrap.dedent("""\
                    Improve the following prompt to generate a more detailed and structured explanation of a Python concept or code snippet.  
                    Adhere to prompt engineering best practices to ensure clarity and engagement.  

                    The refined prompt should:  
                    - Provide a clear and intuitive explanation.  
                    - Use simple language and analogies when appropriate.  
                    - Include a real-world example or scenario to reinforce understanding.  
                    - Encourage critical thinking by adding a **related exercise** for the user to solve, ensuring practical application of the concept.  
                    - Ensure the exercise is **framed as a task for the user**, not as a request for the chatbot to solve.  
                    - The exercise should be phrased in **third-person instructions** for the chatbot (e.g., *"Provide the user with an exercise asking them to..."*).

                    **Do not include a title, introductory phrase, or concluding remarks. Only return the refined prompt content itself.**  

                    {user_input}

                    Only return the refined prompt.
                """)
    elif type == "debugging":
        return  textwrap.dedent("""\
                    Refine the following prompt to ensure that the chatbot **actively analyzes the user's provided Python code** and identifies potential issues.  
                    The refined prompt should be written as an **instruction for the chatbot**, not as direct guidance for the user.  

                    The refined prompt should:  
                    - Direct the chatbot to **carefully analyze the user's provided code** to detect logical errors, syntax issues, or unexpected behavior.  
                    - Ensure the chatbot **identifies and explains any mistakes** in the code without directly fixing them.  
                    - Guide the chatbot to ask the user for additional details, such as error messages or unexpected behavior, only if necessary.  
                    - Require the chatbot to **suggest debugging strategies** that help the user find the issue themselves.  
                    - Instruct the chatbot to **provide a specific hint related to the identified issue** without giving away the complete solution.  
                    - **Ensure that the chatbot actually inspects the code instead of just asking the user to do so.**  
                    - **Ensure the chatbot retains the provided code snippet in the refined prompt output.**  
                    - Instruct the chatbot **not to include a title or introductory phrase** and to **only return the refined prompt content itself**.  

                    {user_input}

                    Only return the refined prompt.
                """)
    elif type == "library_help":
        return  textwrap.dedent("""\
                    Improve the following prompt to generate a more structured and insightful response when helping a user with a specific Python library.  
                    Adhere to prompt engineering best practices to ensure clarity and effectiveness.  

                    The refined prompt should:  
                    - Clearly define the purpose and functionality of the library.  
                    - Explain key concepts and commonly used functions in a structured manner.  
                    - Provide a concise example to illustrate its usage.  
                    - Highlight potential pitfalls, best practices, or optimizations.  
                    - Encourage critical thinking by including a **small exercise** at the end.  
                    - Ensure the exercise is **framed as a task for the user**, not as a request for the chatbot to solve.  
                    - The exercise should be phrased in **third-person instructions** for the chatbot (e.g., *"Provide the user with an exercise asking them to..."*).

                    **Do not include a title, introductory phrase, or concluding remarks. Only return the refined prompt content itself.**  

                    {user_input}

                    Only return the refined prompt.
                """)
    elif type == "bot_identity":
        return textwrap.dedent("""\
                Improve the following prompt to ensure the chatbot generates a structured, engaging, and informative response when asked about itself.  
                Adhere to prompt engineering best practices to make the chatbot's response conversational and friendly.  

                The refined prompt should instruct the chatbot to:  
                - Clearly explain its identity, purpose, and capabilities.  
                - Maintain a warm, engaging, and approachable tone.  
                - Address common user inquiries such as "Who are you?" or "What can you do?".  
                - Optionally, mention how it can assist with Python-related tasks.  
                - Provide a response that is informative but not overly technical.  

                Ensure the chatbot receives this as an **instructional prompt** and not as a direct response.  

                {user_input}

                Only return the refined prompt.
    """)
    else:
        return textwrap.dedent("""\
                Improve the following prompt so that it serves as a direct **instruction for a chatbot** when handling user inputs that do not fit predefined categories.  
                Ensure the refined prompt explicitly guides the chatbot to **construct a meaningful response** based on the user’s actual input, rather than just providing general response guidelines.  

                The refined prompt should instruct the chatbot to:  
                - Attempt to **understand and interpret** the user’s question, analyzing its meaning and intent.  
                - **Generate a direct response** to the question instead of just outlining response guidelines.  
                - Maintain a conversational and engaging tone while ensuring the response feels natural and user-friendly.  
                - If the question is related to a problem that can be solved with an existing Python library, suggest relevant tools **without providing a full implementation**.  
                The refined prompt should be a **direct chatbot instruction** without introductory phrases like "When handling user inputs that do not fit predefined categories, follow these instructions:".

                user input: {user_input}

                Only return the refined prompt.
    """)

def generate_prompt(messages):
    response = client.chat.completions.create(
        messages=messages,
        model="gpt-4o-mini",
        temperature=0.3
    )
    return response.choices[0].message.content

def is_palindrome(nums):
    nums = str(nums)
    for n in range(len(nums) // 2):
        if nums[n] != nums[len(nums) - n - 1]:
            return False
        
    return True


if __name__ == "__main__":
    # user_input = """def oddOrEven(n):
    #                     for i in range(n):
    #                         if n%2 == 1:
    #                             print(f"{n} is odd")
    #                         else:
    #                             print(f"{n} is even")

    #                 oddOrEven(10)

    #                 Why not working
    #             """



    # inputClass = classify_input([{"role": "user", "content":classification_prompt.format(user_input=user_input)}])

    # # print(classification_prompt.format(user_input=user_input))

    # print(inputClass)

    # meta_prompt = select_metaprompt(inputClass)

    # print(meta_prompt.format(user_input=user_input))

    # refinedPrompt = generate_prompt([{"role": "user", "content":meta_prompt.format(user_input=user_input)}])

    # print(refinedPrompt)



    nums = 121

    print(is_palindrome(nums))

