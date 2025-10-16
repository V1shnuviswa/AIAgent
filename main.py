"""
Interactive Mutual Funds Agent with LangChain Zero-Shot Approach
================================================================

This is the main entry point for the Mutual Funds Agent that uses:
- LangChain zero-shot agent pattern
- Moonshot AI LLM for synthesis and general questions
- Production API for fund data
- Tavily web scraping as fallback
- Interactive user experience with confirmations

Author: Mutual Funds Agent
Version: 1.0
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from agent.core import MutualFundsAgent
from agent.config import AgentConfig
from utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

class InteractionMode(Enum):
    CLI = "cli"
    API = "api"
    JUPYTER = "jupyter"

@dataclass
class UserSession:
    session_id: str
    user_name: Optional[str] = None
    interaction_mode: InteractionMode = InteractionMode.CLI
    conversation_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []

class MutualFundsInterface:
    """Main interface for the Interactive Mutual Funds Agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = MutualFundsAgent(config)
        self.current_session: Optional[UserSession] = None
        
    async def start_session(self, user_name: Optional[str] = None, 
                          mode: InteractionMode = InteractionMode.CLI) -> UserSession:
        """Start a new user session"""
        import uuid
        session_id = str(uuid.uuid4())
        self.current_session = UserSession(
            session_id=session_id,
            user_name=user_name,
            interaction_mode=mode
        )
        
        logger.info(f"Started new session: {session_id} for user: {user_name}")
        return self.current_session
    
    async def process_user_input(self, user_input: str) -> str:
        """Process user input and return agent response"""
        if not self.current_session:
            await self.start_session()
        
        try:
            # Add user input to conversation history
            self.current_session.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": self._get_timestamp()
            })
            
            # Process with agent
            response = await self.agent.process_request(
                user_input=user_input,
                session_context=self.current_session.conversation_history,
                user_name=self.current_session.user_name
            )
            
            # Add agent response to history
            self.current_session.conversation_history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": self._get_timestamp()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            return self._generate_error_response(str(e))
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _generate_error_response(self, error: str) -> str:
        """Generate user-friendly error response"""
        return f"""
**Oops! Something went wrong**

I encountered an issue while processing your request: {error}

**What you can do:**
1. 🔄 **Retry** - Try asking your question again
2. 🔍 **Simplify** - Ask about a specific fund with its exact name
3. 🎯 **Be specific** - Include fund name, AMC, or ISIN if known

Would you like to try again with a different question?

---
*If this issue persists, please report it to support.*
"""

async def run_cli_interface():
    """Run the CLI interface for the agent"""
    print("🚀 Welcome to the Interactive Mutual Funds Agent!")
    print("=" * 50)
    print("I can help you with:")
    print("• Fund details and NAV")
    print("• Performance data") 
    print("• Fund comparisons")
    print("• Portfolio holdings")
    print("• General mutual fund questions")
    print("=" * 50)
    
    # Initialize agent
    config = AgentConfig()
    interface = MutualFundsInterface(config)
    
    # Get user name (optional)
    user_name = input("👋 What's your name? (optional, press Enter to skip): ").strip()
    if not user_name:
        user_name = None
    
    # Start session
    session = await interface.start_session(user_name, InteractionMode.CLI)
    
    print(f"\n✨ Session started! Type 'quit' or 'exit' to end.\n")
    
    while True:
        try:
            # Get user input
            user_input = input("🤔 Ask me anything about mutual funds: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Thank you for using the Mutual Funds Agent! Goodbye!")
                break
                
            if not user_input:
                print("Please enter a question or type 'quit' to exit.")
                continue
            
            print("\n🔄 Processing your request...\n")
            
            # Process request
            response = await interface.process_user_input(user_input)
            print(response)
            print("\n" + "─" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            print("Please try again or type 'quit' to exit.\n")

async def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        print("🌐 API mode not implemented yet. Use CLI mode instead.")
        return
    
    await run_cli_interface()

if __name__ == "__main__":
    asyncio.run(main())
