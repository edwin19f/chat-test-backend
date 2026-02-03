from google.adk.agents import LlmAgent
from google.genai import types

def create_tester_agent(tools_list):
    """
    Creates the QA Tester Agent with access to the provided tools.
    
    Args:
        tools_list: A list of AgentTool or FunctionTool instances (e.g. [gmail_tool, calendar_tool])
    """
    
    return LlmAgent(
        model='gemini-2.5-flash',
        name='qa_tester_agent',
        description="A QA agent that tests other agents.",
        instruction=(
            "You are the QA Validator Agent. "
            "Your goal is to rigorously test the functionality of the sub-agents provided to you as tools. "
            
            "**Test Procedure:**"
            "1. **Test Calendar Agent**: Call providing a safe, read-only request like 'List upcoming events'. Verify it returns a list (empty or not)."
            "2. **Test Gmail Agent**: Call providing a safe, read-only request like 'List unread emails'. Verify it returns a list."
            
            "**Rules:**"
            "- Perform the tests sequentially (one after another)."
            "- If a sub-agent asks for clarification, provide reasonable dummy data (e.g., 'test event', 'test body')."
            "- **CRITICAL**: Limit yourself to 4 interactions/steps total. If a test fails or stalls, report the failure and move on or stop."
            "- After running the tests, output a FINAL REPORT summarizing: [Pass/Fail] for each agent."
            
            "Do not ask the user for input. YOU are the user's proxy for testing."
        ),
        tools=tools_list,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.1, # Low temperature for consistent testing
            max_output_tokens=1000
        )
    )
