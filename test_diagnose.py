import sys
import os
from dotenv import load_dotenv

# Add the directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def diagnose():
    print("--- Diagnosing Agent Structure ---")
    
    try:
        from agent import root_agent, gmail_tool, calendar_tool
        print("Successfully imported root_agent.")
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import agent.py: {e}")
        return

    print(f"Root Agent Name: {root_agent.name}")
    print(f"Root Agent Model: {root_agent.model}")
    print(f"Root Agent Tools Count: {len(root_agent.tools)}")
    
    for i, tool in enumerate(root_agent.tools):
        print(f"  Tool {i+1}: {tool}")
        # Check if it has a name
        if hasattr(tool, 'name'):
             print(f"    Name: {tool.name}")
        # If it is an AgentTool, check the inner agent
        if hasattr(tool, '_agent'):
             print(f"    Inner Agent: {tool._agent.name}")

    print("\n--- Testing Calendar Agent Loading ---")
    try:
        from subagents.calendar_subagent import calendar_agent
        print(f"Calendar Agent loaded: {calendar_agent.name}")
        print(f"Calendar Agent Tools: {len(calendar_agent.tools)}")
    except Exception as e:
        print(f"Error loading calendar_subagent: {e}")

if __name__ == "__main__":
    diagnose()
