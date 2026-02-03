import sys
import os

# Ensure we can import from local subdirectories
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    print("Attempting to import root_agent...")
    from agent import root_agent
    print(f"✅ Successfully imported root_agent: {root_agent.name}")
    
    print(f"Tools loaded: {[t.name for t in root_agent.tools]}")
    
    if len(root_agent.tools) == 2:
        print("✅ Correct number of tools (sub-agents) loaded.")
    else:
        print(f"⚠️ Warning: Expected 2 tools, found {len(root_agent.tools)}")

except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
