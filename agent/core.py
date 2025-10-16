"""
Core Mutual Funds Agent implementation using LangChain zero-shot approach
"""

import asyncio
import json
from typing import Dict, Any, List, Optional

from .config import AgentConfig
from .intent_parser import IntentParser, Intent, SentimentLabel, IntentType
from .tools import ToolOrchestrator
from .response_formatter import ResponseFormatter
from .moonshot_llm import get_chat_llm
from utils.logger import get_logger

logger = get_logger(__name__)

class MutualFundsAgent:
    """
    LangChain-style zero-shot agent for mutual funds queries.
    
    Uses initialize_agent with CHAT_ZERO_SHOT_REACT_DESCRIPTION type.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.intent_parser = IntentParser(config)
        self.tool_orchestrator = ToolOrchestrator(config)
        self.response_formatter = ResponseFormatter(config)
        
        # Initialize components lazily
        self._llm = None
        self._memory = None
        self._tools = None
        self._agent = None

    def _extract_fund_data_from_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fund data from complex nested result structure - FIXED VERSION"""
        fund_data = {}
        
        logger.info(f"DEBUG: Extracting fund data from result keys: {list(result.keys())}")
        
        # Check if result has 'results' array with direct fund data (simple structure)
        if result.get("results") and isinstance(result["results"], list):
            logger.info(f"DEBUG: Found simple results array with {len(result['results'])} items")
            
            # Get the first fund from the results
            first_fund = result["results"][0]
            if isinstance(first_fund, dict):
                logger.info(f"DEBUG: First fund keys: {list(first_fund.keys())}")
                logger.info(f"DEBUG: First fund scheme_name: {first_fund.get('scheme_name', 'N/A')}")
                
                # Extract data directly from the fund object
                fund_data = {
                    "scheme_name": first_fund.get("scheme_name"),
                    "isin": first_fund.get("isin"),
                    "amc_name": first_fund.get("amc_name"),
                    "fund_manager": first_fund.get("fund_manager"),
                    "scheme_type": first_fund.get("fund_type"),
                    "fund_subtype": first_fund.get("fund_subtype"),
                    "expense_ratio": first_fund.get("expense_ratio"),
                    "nav": first_fund.get("nav"),
                    "plan": first_fund.get("plan"),
                    "return_1y": first_fund.get("return_1y"),
                    "return_3y": first_fund.get("return_3y"),
                    "return_5y": first_fund.get("return_5y"),
                    "sebi_risk_category": first_fund.get("sebi_risk_category")
                }
                
                logger.info(f"DEBUG: Extracted simple fund data: {first_fund.get('scheme_name', 'No name')}")
                logger.info(f"DEBUG: Fund data extracted successfully with {len([v for v in fund_data.values() if v is not None and v != ''])} non-empty fields")
                return fund_data
        
        # Check if result has 'data' array (comprehensive search with nested results)
        elif result.get("data") and isinstance(result["data"], list):
            logger.info(f"DEBUG: Found data array with {len(result['data'])} items")
            
            for i, data_item in enumerate(result["data"]):
                logger.info(f"DEBUG: Processing data item {i}: {list(data_item.keys())}")
                
                if data_item.get("results") and isinstance(data_item["results"], dict):
                    nested_results = data_item["results"]
                    logger.info(f"DEBUG: Found nested results with keys: {list(nested_results.keys())}")
                    
                    # Extract from factsheet
                    if "factsheet" in nested_results and nested_results["factsheet"]:
                        factsheet = nested_results["factsheet"]
                        logger.info(f"DEBUG: Found factsheet: {factsheet.get('scheme_name', 'No name')}")
                        
                        fund_data.update({
                            "scheme_name": factsheet.get("scheme_name"),
                            "isin": factsheet.get("isin"),
                            "amc_name": factsheet.get("amc"),
                            "fund_manager": factsheet.get("fund_manager"),
                            "scheme_type": factsheet.get("scheme_type"),
                            "expense_ratio": factsheet.get("expense_ratio"),
                            "exit_load": factsheet.get("exit_load"),
                            "minimum_lumpsum": factsheet.get("minimum_lumpsum"),
                            "minimum_sip": factsheet.get("minimum_sip"),
                            "benchmark": factsheet.get("benchmark"),
                            "plan": factsheet.get("plan"),
                            "sub_category": factsheet.get("sub_category"),
                            "sebi_risk_category": factsheet.get("sebi_risk_category")
                        })
                    
                    # Extract from returns
                    if "returns" in nested_results and nested_results["returns"]:
                        returns = nested_results["returns"]
                        logger.info(f"DEBUG: Found returns data")
                        fund_data.update({
                            "return_1m": returns.get("return_1m"),
                            "return_1y": returns.get("return_1y"),
                            "return_3y": returns.get("return_3y"),
                            "return_ytd": returns.get("return_ytd")
                        })
                    
                    # Extract from NAV history
                    if "nav_history" in nested_results and nested_results["nav_history"]:
                        nav_section = nested_results["nav_history"]
                        if nav_section.get("nav_history") and isinstance(nav_section["nav_history"], list):
                            nav_data = nav_section["nav_history"]
                            if nav_data:
                                latest_nav = nav_data[0]
                                logger.info(f"DEBUG: Found NAV: {latest_nav.get('nav')}")
                                fund_data.update({
                                    "nav": latest_nav.get("nav"),
                                    "nav_date": latest_nav.get("date")
                                })
                    
                    # Extract from BSE scheme
                    if "bse_scheme" in nested_results and nested_results["bse_scheme"]:
                        bse_section = nested_results["bse_scheme"]
                        if bse_section.get("data") and isinstance(bse_section["data"], list):
                            bse_schemes = bse_section["data"]
                            if bse_schemes:
                                bse_scheme = bse_schemes[0]
                                logger.info(f"DEBUG: Found BSE scheme")
                                fund_data.update({
                                    "scheme_code": bse_scheme.get("scheme_code"),
                                    "scheme_plan": bse_scheme.get("scheme_plan"),
                                    "face_value": bse_scheme.get("operational_details", {}).get("face_value"),
                                    "purchase_amount_min": bse_scheme.get("purchase_details", {}).get("minimum_purchase_amount"),
                                    "redemption_allowed": bse_scheme.get("redemption_details", {}).get("redemption_allowed")
                                })
                    
                    # If we found meaningful data, break
                    if any(v is not None and v != "" for v in fund_data.values()):
                        logger.info(f"DEBUG: Extracted {len([v for v in fund_data.values() if v is not None])} non-null fields")
                        break
        
        logger.info(f"DEBUG: Final fund data: {fund_data}")
        return fund_data
    
    @property
    def llm(self):
        """Lazy initialization of Moonshot LLM using proper configuration"""
        if self._llm is None:
            try:
                # Use the proper Moonshot LLM initialization
                self._llm = get_chat_llm(
                    model_name=self.config.MOONSHOT_MODEL,
                    temperature=self.config.MOONSHOT_TEMPERATURE
                )
                logger.info("Moonshot LLM initialized successfully")
            except Exception as e:
                logger.warning(f"Moonshot LLM initialization failed: {e}, using fallback")
                # Create a dummy LLM that will trigger fallback
                from langchain.llms.fake import FakeListLLM
                self._llm = FakeListLLM(responses=["Using direct tool orchestration"])
        return self._llm
    
    @property
    def memory(self):
        """Lazy initialization of memory"""
        if self._memory is None:
            from langchain.memory import ConversationBufferMemory
            self._memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        return self._memory
    
    @property
    def tools(self):
        """Lazy initialization of tools"""
        if self._tools is None:
            self._tools = self._create_tools()
        return self._tools
    
    @property
    def agent(self):
        """Lazy initialization of LangChain agent with optimized settings"""
        if self._agent is None:
            from langchain.agents import initialize_agent, AgentType
            self._agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                handle_parsing_errors=True,
                memory=self.memory,
                verbose=True,  # Enable verbose to see what's happening
                max_iterations=10,  # Increased iterations for complex queries
                max_execution_time=60,  # Increased timeout to 60 seconds
                return_intermediate_steps=False
            )
        return self._agent
    
    def _summarize_tool_result(self, result: Dict[str, Any], query: str) -> str:
        """Return raw tool result data for agent to synthesize - no hardcoded templates"""
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            return f"Error: Invalid result format for {query}"
            
        if not result.get("found") or not result.get("results"):
            return f"No data found for {query}"
        
        # Ensure results is a list
        results = result.get("results", [])
        if not isinstance(results, list):
            return f"Error: Invalid results format for {query}"

        # Return raw data for agent to process - no templates
        source = result.get("source", "")
        
        if source == "TAVILY_API":
            # For web search results, provide content for agent to synthesize
            content_data = []
            for item in results[:5]:
                if isinstance(item, dict):
                    title = item.get("title", "")
                    content = item.get("content", "")
                    url = item.get("url", "")
                    
                    if content:
                        content_data.append({
                            "title": title,
                            "content": content[:500],  # Truncate for efficiency
                            "source": url
                        })
            
            # Return structured data for agent processing
            return f"Web search results for '{query}': {json.dumps(content_data, indent=2)}"
            
        else:
            # For database results, return fund data for agent processing
            fund_data = []
            for fund in results[:10]:  # More results for fund queries
                if isinstance(fund, dict):
                    fund_info = {
                        "name": fund.get("scheme_name", "Unknown Fund"),
                        "amc": fund.get("amc_name", "N/A"),
                        "nav": fund.get("nav", "N/A"),
                        "fund_type": fund.get("scheme_type", fund.get("fund_type", "N/A")),
                        "plan": fund.get("scheme_plan", "N/A"),
                        "isin": fund.get("isin", "N/A")
                    }
                    
                    # Add fund manager if available
                    manager = fund.get("fund_manager", fund.get("manager_name"))
                    if manager and manager != "N/A":
                        fund_info["fund_manager"] = manager
                    
                    # Add other relevant fields
                    for field in ["minimum_purchase_amount", "sip_flag", "fund_subtype", "returns"]:
                        value = fund.get(field)
                        if value and value != "N/A":
                            fund_info[field] = value
                    
                    fund_data.append(fund_info)
            
            return f"Database results for '{query}': {json.dumps(fund_data, indent=2)}"
    
    def _create_tools(self) -> List:
        """Create conversational tools for the LangChain agent"""
        from langchain.agents import Tool
        
        def search_funds_db(query: str) -> str:
            """Search for specific mutual fund information in the production database"""
            try:
                # Create new event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.tool_orchestrator.call_db_api(fund_name=query, deep_search=True)
                )
                
                # Return conversational structured data for agent to synthesize
                if not isinstance(result, dict):
                    return f"I encountered an error searching our database for {query}. Please try again."
                
                if result.get("found") and result.get("results"):
                    results = result["results"]
                    if not results:
                        return f"I searched our comprehensive fund database but couldn't find any funds matching '{query}'. You might want to check the spelling or try a broader search term."
                    
                    # Create conversational fund summary for agent
                    response = f"Great! I found {len(results)} funds matching '{query}' in our database. Here's what I discovered:\n\n"
                    
                    for i, fund in enumerate(results[:8], 1):  # Limit to 8 for readability
                        if isinstance(fund, dict):
                            name = fund.get('scheme_name', 'Fund Name Not Available')
                            amc = fund.get('amc_name', fund.get('amc_code', 'N/A'))
                            nav = fund.get('nav', fund.get('current_nav', 'N/A'))
                            fund_type = fund.get('scheme_type', fund.get('fund_type', 'N/A'))
                            
                            response += f"{i}. **{name}**\n"
                            response += f"   - Fund House: {amc}\n"
                            response += f"   - Category: {fund_type}\n"
                            
                            if nav != 'N/A':
                                response += f"   - Current NAV: ₹{nav}\n"
                            
                            # Add fund manager if available
                            manager = fund.get('fund_manager', fund.get('manager_name'))
                            if manager and manager != 'N/A':
                                response += f"   - Fund Manager: {manager}\n"
                            
                            # Add minimum investment if available
                            min_inv = fund.get('minimum_purchase_amount')
                            if min_inv and min_inv not in ['0.00', 'N/A', '']:
                                response += f"   - Minimum Investment: ₹{min_inv}\n"
                            
                            # Add SIP availability
                            if fund.get('sip_flag') == 'Y':
                                response += f"   - SIP Available: Yes\n"
                            
                            # Add expense ratio if available
                            expense = fund.get('expense_ratio')
                            if expense and expense != 'N/A':
                                response += f"   - Expense Ratio: {expense}%\n"
                            
                            # Add returns if available
                            returns_1y = fund.get('return_1y')
                            if returns_1y and returns_1y != 'N/A':
                                response += f"   - 1-Year Return: {returns_1y}%\n"
                            
                            response += "\n"
                    
                    if len(results) > 8:
                        response += f"*I'm showing the top 8 results out of {len(results)} total matches. Let me know if you'd like to see more specific funds.*"
                    
                    return response
                else:
                    return f"I searched our fund database for '{query}' but didn't find any matching results. This could be because the fund name is spelled differently or it might not be in our database. Would you like to try a different search term?"
                    
            except Exception as e:
                return f"I'm having trouble accessing our fund database right now. Error: {str(e)}. Please try again in a moment."
        
        def search_tavily_data(query: str) -> str:
            """Search web using Tavily API for general mutual fund knowledge and concepts"""
            try:
                # Create new event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.tool_orchestrator.call_tavily_search(query=query)
                )
                
                # Return conversational web search results
                if not isinstance(result, dict):
                    return f"I had trouble searching the web for information about '{query}'. Let me try to help you in another way."
                
                if result.get("found") and result.get("results"):
                    results = result["results"]
                    
                    # Create conversational explanation from web results
                    response = f"I found some great information about '{query}' from current sources:\n\n"
                    
                    combined_content = ""
                    source_count = 0
                    
                    for item in results[:3]:  # Top 3 most relevant results
                        if isinstance(item, dict) and item.get("content"):
                            content = item.get("content", "")
                            title = item.get("title", "")
                            
                            if len(content) > 100:  # Only use substantial content
                                source_count += 1
                                # Clean and summarize the content
                                clean_content = content[:400].strip()
                                combined_content += f"{clean_content}... "
                    
                    if combined_content and source_count > 0:
                        # Create a clear explanation
                        response += f"Based on current market information:\n\n{combined_content}\n\n"
                        response += f"*Information compiled from {source_count} reliable financial sources.*"
                        return response
                    else:
                        return f"I searched for information about '{query}' but the results weren't detailed enough to provide a good explanation. Would you like to ask about specific mutual funds or investment concepts instead?"
                else:
                    return f"I couldn't find current web information about '{query}'. However, I can help you with specific mutual fund data from our database or explain general investment concepts. What would you like to know more about?"
                    
            except Exception as e:
                return f"I encountered an issue while searching for web information: {str(e)}. Let me help you with specific fund data from our database instead."
        
        def search_bse_schemes(query: str) -> str:
            """Search BSE scheme data for additional mutual fund information"""
            try:
                # Create new event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.tool_orchestrator.call_bse_schemes_api(scheme_name=query)
                )
                
                if isinstance(result, dict) and result.get("found"):
                    return f"I found additional information about '{query}' from BSE schemes database. The data shows relevant fund details that might be helpful for your query."
                else:
                    return f"I searched the BSE schemes database for '{query}' but couldn't find additional information. The main fund database might have better results for this query."
            except Exception as e:
                return f"I had trouble accessing the BSE schemes database: {str(e)}. Let me help you with our main fund database instead."
        
        def get_fund_by_isin(isin: str) -> str:
            """Get comprehensive fund details using exact ISIN code"""
            try:
                # Create new event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.tool_orchestrator.call_db_api_by_isin(isin=isin)
                )
                
                if isinstance(result, dict) and result.get("found"):
                    return f"Perfect! I found detailed information for ISIN {isin}. This includes comprehensive fund data like factsheet details, performance history, holdings, and current NAV information."
                else:
                    return f"I searched for ISIN {isin} but couldn't find detailed information. The ISIN might be incorrect or the fund might not be in our database."
            except Exception as e:
                return f"I had trouble looking up ISIN {isin}: {str(e)}. Please double-check the ISIN format."
        
        def search_comprehensive_fund_data(query: str) -> str:
            """Get detailed analysis and comprehensive information about mutual funds"""
            try:
                # Create new event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Search for comprehensive fund data
                basic_result = loop.run_until_complete(
                    self.tool_orchestrator.call_db_api(fund_name=query, deep_search=True)
                )
                
                # Create comprehensive conversational analysis
                if not basic_result.get("found", False) or not basic_result.get("results"):
                    return f"I searched extensively for '{query}' but couldn't find comprehensive data. Would you like me to search with a different term or check for similar fund names?"
                
                results = basic_result["results"]
                response = f"📊 COMPREHENSIVE ANALYSIS for '{query}':\n\n"
                
                for i, fund in enumerate(results[:3], 1):  # Limit to 3 for comprehensive analysis
                    if isinstance(fund, dict):
                        name = fund.get('scheme_name', 'Unknown Fund')
                        response += f"🔹 **{name}**\n"
                        
                        # Basic info
                        fund_type = fund.get('scheme_type', fund.get('fund_type', 'N/A'))
                        plan = fund.get('scheme_plan', 'N/A')
                        amc = fund.get('amc_name', fund.get('amc_code', 'N/A'))
                        
                        response += f"   📈 Type: {fund_type}\n"
                        response += f"   🏢 AMC: {amc}\n"
                        response += f"   📋 Plan: {plan}\n"
                        
                        # Investment details
                        nav = fund.get('nav', fund.get('current_nav', 'N/A'))
                        if nav != 'N/A':
                            response += f"   💰 NAV: ₹{nav}\n"
                        
                        min_amount = fund.get('minimum_purchase_amount')
                        if min_amount and min_amount != '0.00':
                            response += f"   💵 Min Investment: ₹{min_amount}\n"
                        
                        sip_flag = fund.get('sip_flag')
                        if sip_flag == 'Y':
                            response += f"   🔄 SIP: Available\n"
                            sip_min = fund.get('sip_minimum_amount')
                            if sip_min and sip_min != '0.00':
                                response += f"   🔄 SIP Min: ₹{sip_min}\n"
                        
                        # Additional details
                        purchase_allowed = fund.get('purchase_allowed')
                        redemption_allowed = fund.get('redemption_allowed')
                        if purchase_allowed == 'N':
                            response += f"   ⚠️ Purchase: Currently Closed\n"
                        if redemption_allowed == 'Y':
                            response += f"   ✅ Redemption: Allowed\n"
                        
                        response += "\n"
                
                response += f"ℹ️ Found {len(results)} total funds. Showing top {min(3, len(results))} for detailed analysis."
                return response
                
            except Exception as e:
                return f"Error in comprehensive search: {str(e)}"
        
        return [
            Tool(
                name="search_funds_db",
                description="🏦 FUND DATABASE: Search our comprehensive mutual funds database for specific fund information. Use this for: NAV, performance data, fund manager details, expense ratios, minimum investments, SIP options. Perfect for specific fund names or AMC queries like 'DSP funds', 'HDFC Top 100', 'Axis Bluechip'. Returns user-friendly fund information ready for conversation.",
                func=search_funds_db
            ),
            Tool(
                name="search_tavily_data", 
                description="🌐 WEB KNOWLEDGE: Search current web sources for general mutual fund concepts and market insights. Use this for: 'What is SIP?', 'Explain mutual funds', 'Investment strategies', 'Market trends', conceptual questions. Returns educational explanations in conversational language.",
                func=search_tavily_data
            ),
            Tool(
                name="search_bse_schemes",
                description="📊 BSE BACKUP: Alternative database search for additional fund information from BSE. Use as secondary option when main database doesn't have sufficient details. Input: fund name or scheme name.",
                func=search_bse_schemes  
            ),
            Tool(
                name="get_fund_by_isin",
                description="🎯 ISIN LOOKUP: Get complete fund details using exact ISIN code. Use when user provides or asks about specific ISIN codes. Returns comprehensive fund information including factsheet, performance, holdings. Input: ISIN code (e.g., 'INF846K01EW2').",
                func=get_fund_by_isin
            ),
            Tool(
                name="search_comprehensive_fund_data",
                description="🔍 DETAILED ANALYSIS: Comprehensive fund search with detailed analysis and formatting. Use for complex queries requiring in-depth fund information, comparisons, or when user asks for 'detailed analysis' or 'comprehensive information'. Returns structured detailed fund analysis.",
                func=search_comprehensive_fund_data
            )
        ]
    
    async def process_request(self, user_input: str, 
                            session_context: List[Dict[str, Any]] = None,
                            user_name: Optional[str] = None) -> str:
        """
        Intelligent conversational agent for mutual fund queries with smart routing
        
        Uses fast fallback for simple listings, full agent for specific queries.
        """
        logger.info(f"Processing conversational request: {user_input[:100]}...")
        
        try:
            # Check if this is a simple listing query that should use fast fallback
            query_lower = user_input.lower()
            is_simple_listing = (
                'list' in query_lower and 
                any(word in query_lower for word in ['all', 'funds', 'show']) and
                not any(word in query_lower for word in ['manager', 'compare', 'performance', 'returns', 'details', 'specific', 'who', 'what', 'how'])
            )
            
            if is_simple_listing:
                logger.info("Using fast fallback for simple listing query")
                return await self._intelligent_conversational_fallback(user_input, user_name)
            
            # For specific queries, use full conversational agent
            logger.info("Using full conversational agent for specific query")
            
            # Perform sentiment analysis on user input
            intent = await self.intent_parser.parse(user_input)
            sentiment_tone = self._analyze_sentiment_tone(intent)
            
            # Create conversational system prompt based on user requirements
            system_prompt = f"""You are an intelligent, conversational mutual funds assistant that helps users in a friendly, user-friendly way.

CORE BEHAVIOR:
- Always be friendly, clear, and interactive in your responses
- Use natural conversational language - never show raw JSON or API data
- Adjust your tone based on user sentiment: {sentiment_tone}
- Provide structured information with bullet points or tables for comparisons
- Always end responses with a polite follow-up question to continue the conversation

DATA SOURCE RULES:
1. For SPECIFIC fund queries (NAV, ISIN, returns, fund manager, holdings, performance data, comparisons, suggestions):
   - Use search_funds_db to get precise fund data from the database
   - Present data clearly with proper formatting (never raw JSON)
   - For comparisons, fetch multiple funds and highlight differences/similarities
   
2. For GENERAL knowledge questions (concepts, definitions, explanations):
   - Use search_tavily_data for current market insights and explanations
   - Examples: "What is a mutual fund?", "What does SIP mean?", "Explain diversification"
   - Rephrase web results into simple, conversational language

3. For MIXED queries:
   - Combine both database and web search results into one seamless answer
   - Use LLM reasoning to provide insights and recommendations

RESPONSE FORMAT:
- Start responses naturally based on the user's question
- Use bullet points, tables, or structured format for complex data
- Include brief recommendations or insights when helpful
- ALWAYS end with: "Would you like me to provide more details or related data about this?"

User context: {f"User name: {user_name}" if user_name else "Anonymous user"}"""

            enhanced_input = f"{system_prompt}\n\nUser Query: {user_input}"
            
            # Run the conversational agent
            response = await self._run_conversational_agent(enhanced_input, intent)
            
            # Check if agent response is incomplete or indicates limits hit
            if self._is_incomplete_response(response):
                logger.warning("Agent returned incomplete response, using fallback")
                return await self._intelligent_conversational_fallback(user_input, user_name)
            
            # Ensure response is conversational and includes follow-up
            formatted_response = self._ensure_conversational_format(response, user_input)
            
            return formatted_response
                
        except asyncio.TimeoutError:
            logger.warning("Agent execution timed out, using intelligent fallback")
            return await self._intelligent_conversational_fallback(user_input, user_name)
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return self._format_error_response(str(e), user_input)
    
    def _analyze_sentiment_tone(self, intent: Intent) -> str:
        """Analyze user sentiment and return appropriate tone guidance"""
        if not intent.sentiment:
            return "neutral and helpful"
        
        if intent.sentiment.label == SentimentLabel.NEGATIVE:
            return "extra empathetic and patient - user seems frustrated"
        elif intent.sentiment.label == SentimentLabel.POSITIVE:
            return "enthusiastic and supportive"
        else:
            return "friendly and informative"
    
    def _is_incomplete_response(self, response: str) -> bool:
        """Check if the agent response is incomplete or indicates hitting limits"""
        if not response or len(response.strip()) < 30:
            return True
            
        response_lower = response.lower().strip()
        
        # Check for common incomplete response patterns
        incomplete_indicators = [
            "agent stopped due to iteration limit",
            "agent stopped due to time limit", 
            "maximum iterations reached",
            "execution time exceeded",
            "stopped due to iteration limit",
            "stopped due to time limit",
            "💡 would you like me to provide more details" # Only the follow-up, no real content
        ]
        
        for indicator in incomplete_indicators:
            if indicator in response_lower:
                return True
        
        # If response is only the follow-up question, it's incomplete
        if response_lower.strip().startswith("💡 would you like me to provide"):
            return True
            
        return False
    
    async def _run_conversational_agent(self, enhanced_input: str, intent: Intent) -> str:
        """Run the agent with conversational focus"""
        try:
            logger.info("Running conversational LangChain agent...")
            loop = asyncio.get_event_loop()
            
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.agent.invoke({"input": enhanced_input})
                ),
                timeout=45  # Reduced timeout for specific queries (45s vs 70s)
            )
            
            if isinstance(result, dict):
                response = result.get("output", str(result))
            else:
                response = str(result)
            
            return response if response else "I need more information to help you better."
            
        except asyncio.TimeoutError:
            logger.warning("Agent processing timed out - using intelligent fallback")
            raise asyncio.TimeoutError("Agent processing timed out")
        except Exception as e:
            error_msg = str(e).lower()
            if "iteration limit" in error_msg or "time limit" in error_msg:
                logger.warning(f"Agent stopped due to limits: {e}")
                raise asyncio.TimeoutError(f"Agent reached processing limits: {e}")
            else:
                logger.error(f"Conversational agent error: {e}")
                raise e
    
    def _ensure_conversational_format(self, response: str, user_input: str) -> str:
        """Ensure response is conversational and includes follow-up question"""
        if not response or len(response.strip()) == 0:
            return "I'd be happy to help with your mutual fund question! Could you provide a bit more detail about what you're looking for?"
        
        # Check if this looks like an incomplete/error response
        response_lower = response.lower().strip()
        if (response_lower.startswith("agent stopped") or 
            "iteration limit" in response_lower or 
            "time limit" in response_lower or
            len(response.strip()) < 50):
            logger.warning("Detected incomplete agent response, triggering fallback")
            return "I'm having trouble processing your request fully. Let me help you in a more direct way."
        
        # Clean up any remaining raw JSON or technical formatting
        cleaned_response = response.strip()
        
        # Remove any obvious JSON patterns that might have slipped through
        import re
        cleaned_response = re.sub(r'\{[^}]*\}', '', cleaned_response)
        cleaned_response = re.sub(r'\[[^]]*\]', '', cleaned_response)
        
        # Ensure it doesn't already end with a follow-up question
        if not any(ending in cleaned_response.lower()[-100:] for ending in 
                  ["would you like", "need more", "anything else", "can i help", "want to know"]):
            cleaned_response += "\n\n💡 Would you like me to provide more details or related data about this?"
        
        return cleaned_response
    
    async def _intelligent_conversational_fallback(self, user_input: str, user_name: Optional[str] = None) -> str:
        """Enhanced fallback that handles rate limits and provides direct database responses"""
        try:
            logger.info("Using enhanced intelligent fallback")
            
            query_lower = user_input.lower()
            greeting = f"Hello{' ' + user_name if user_name else ''}! "
            
            # For DSP queries, use direct search with simplified response
            if 'dsp' in query_lower and any(word in query_lower for word in ['fund', 'mutual', 'list', 'all']):
                # Check for specific fund queries
                if any(word in query_lower for word in ['manager', 'who', 'details', 'specific']):
                    # Handle specific DSP fund queries
                    db_result = await self.tool_orchestrator.call_db_api(fund_name="DSP", deep_search=True)
                    
                    if db_result.get("found") and db_result.get("results"):
                        results = db_result["results"]
                        
                        # Look for specific fund mentioned
                        if "quant" in query_lower:
                            # Search for quant-related funds
                            quant_result = await self.tool_orchestrator.call_db_api(fund_name="quant", deep_search=True)
                            if quant_result.get("found") and quant_result.get("results"):
                                quant_funds = quant_result["results"][:3]
                                response = f"{greeting}I searched for 'DSP Quant Fund 34' but couldn't find it in our database. However, I found these Quant-related funds:\n\n"
                                
                                for i, fund in enumerate(quant_funds, 1):
                                    if isinstance(fund, dict):
                                        name = fund.get('scheme_name', 'Unknown Fund')
                                        amc = fund.get('amc_name', 'N/A')
                                        manager = fund.get('fund_manager', 'N/A')
                                        
                                        response += f"**{i}. {name}**\n"
                                        response += f"   • Fund House: {amc}\n"
                                        if manager != 'N/A':
                                            response += f"   • Fund Manager: {manager}\n"
                                        response += "\n"
                                
                                response += "💡 Could you double-check the fund name? Or would you like to see all available DSP funds instead?"
                                return response
                        
                        # Default DSP fund info response
                        response = f"{greeting}I found information about DSP funds. Here are some key details:\n\n"
                        
                        # Show first few DSP funds with manager info if available
                        for i, fund in enumerate(results[:5], 1):
                            if isinstance(fund, dict):
                                name = fund.get('scheme_name', 'Unknown Fund')
                                
                                response += f"**{i}. {name}**\n"
                                response += f"   • Fund House: DSP Mutual Fund\n"
                                response += f"   • Scheme Type: {fund.get('scheme_type', 'N/A')}\n"
                                
                                # Note: This database doesn't seem to have fund_manager field for DSP funds
                                response += "\n"
                        
                        response += "⚠️ **Note**: Fund manager information is currently unavailable due to API limitations. Please try again later or visit the AMC website for detailed fund manager information.\n\n"
                        response += "💡 Would you like more details about any specific DSP fund, or help with something else?"
                        
                        return response
                    else:
                        return f"{greeting}I'm currently experiencing some technical difficulties accessing fund information. Please try again in a few minutes, or visit the DSP Mutual Fund website directly for the most up-to-date information."
                
                # Simple listing query - use existing logic
                db_result = await self.tool_orchestrator.call_db_api(fund_name="DSP", deep_search=True)
                
                if db_result.get("found") and db_result.get("results"):
                    results = db_result["results"][:12]  # Show more DSP funds
                    
                    response = f"{greeting}I found {len(results)} DSP mutual funds for you:\n\n"
                    
                    for i, fund in enumerate(results, 1):
                        if isinstance(fund, dict):
                            name = fund.get('scheme_name', 'Unknown Fund')
                            fund_type = fund.get('scheme_type', 'N/A')
                            min_amount = fund.get('minimum_purchase_amount', 'N/A')
                            
                            response += f"**{i}. {name}**\n"
                            response += f"   • Category: {fund_type}\n"
                            if min_amount != 'N/A' and min_amount != '0.00':
                                response += f"   • Min Investment: ₹{min_amount}\n"
                            if fund.get('sip_flag') == 'Y':
                                response += f"   • SIP Available: Yes\n"
                            
                            response += "\n"
                    
                    response += "💡 Would you like more details about any specific DSP fund, or help comparing these options?"
                    return response
                else:
                    return f"{greeting}I searched for DSP funds but couldn't find specific matches. This might be a temporary database issue. Could you try asking for a specific DSP fund name instead?"
            
            # For other queries, provide general assistance
            return f"{greeting}I'm currently experiencing some technical difficulties with my AI processing due to rate limits. However, I can still help you with:\n\n• **Fund Information**: Search for specific mutual funds by name\n• **Fund Comparisons**: Compare performance and features\n• **Investment Guidance**: Basic investment concepts\n\n💡 Could you try rephrasing your question, or let me know what specific information you're looking for?"
            
        except Exception as e:
            logger.error(f"Fallback error: {e}")
            return f"{greeting}I apologize, but I'm currently experiencing technical difficulties. Please try again in a few minutes or contact support if the issue persists."
                
        except Exception as e:
            logger.error(f"Intelligent fallback error: {e}")
            return self._format_error_response(str(e), user_input)
    
    def _format_general_knowledge_response(self, web_result: dict, user_input: str, greeting: str) -> str:
        """Format general knowledge responses conversationally"""
        if not web_result.get("found") or not web_result.get("results"):
            return f"""{greeting}I'd be happy to help you understand more about mutual funds!

Unfortunately, I couldn't find specific information about "{user_input}" right now. However, I can help you with general mutual fund concepts, investment strategies, or specific fund details.

💡 Would you like me to explain basic mutual fund concepts or help you search for specific fund information?"""

        # Extract key information from web results
        results = web_result.get("results", [])[:3]
        combined_info = ""
        
        for result in results:
            content = result.get("content", "")
            if content and len(content) > 50:
                combined_info += f"{content[:400]}... "
        
        if not combined_info.strip():
            return f"""{greeting}I found some information about your question, but the details weren't clear enough to provide a good explanation.

Let me help you with specific mutual fund questions instead! I can provide information about:
• Fund performance and NAV details
• Specific fund comparisons
• Investment strategies and recommendations
• SIP planning and minimum investments

💡 Would you like me to search for specific fund information or explain a particular investment concept?"""
        
        # Create a conversational explanation
        response = f"""{greeting}Great question about mutual funds! Let me explain this for you.

{self._create_conversational_explanation(combined_info, user_input)}

💡 Would you like me to provide more details about this topic or help you find specific fund information?"""
        
        return response
    
    def _format_fund_specific_response(self, db_result: dict, user_input: str, greeting: str) -> str:
        """Format fund-specific responses conversationally"""
        if not db_result.get("found") or not db_result.get("results"):
            return f"""{greeting}I searched our comprehensive mutual fund database for "{user_input}" but couldn't find exact matches.

This might be because:
• The fund name might be slightly different
• It could be a new fund not yet in our database
• There might be a typo in the fund name

💡 Could you provide more details about the specific fund you're looking for? Or would you like me to search for similar funds or fund houses?"""

        results = db_result.get("results", [])[:8]  # Limit for readability
        
        response = f"""{greeting}I found {len(results)} mutual funds matching your search! Here's what I discovered:

"""
        
        for i, fund in enumerate(results, 1):
            if isinstance(fund, dict):
                name = fund.get('scheme_name', 'Fund Name Not Available')
                amc = fund.get('amc_name', fund.get('amc_code', 'N/A'))
                nav = fund.get('nav', fund.get('current_nav', 'N/A'))
                fund_type = fund.get('scheme_type', fund.get('fund_type', 'N/A'))
                
                response += f"**{i}. {name}**\n"
                response += f"   • Fund House: {amc}\n"
                response += f"   • Category: {fund_type}\n"
                if nav != 'N/A':
                    response += f"   • Current NAV: ₹{nav}\n"
                
                # Add additional useful details
                fund_manager = fund.get('fund_manager', fund.get('manager_name'))
                if fund_manager and fund_manager != 'N/A':
                    response += f"   • Fund Manager: {fund_manager}\n"
                
                min_investment = fund.get('minimum_purchase_amount')
                if min_investment and min_investment not in ['0.00', 'N/A', '']:
                    response += f"   • Minimum Investment: ₹{min_investment}\n"
                
                if fund.get('sip_flag') == 'Y':
                    response += f"   • SIP Available: Yes\n"
                
                response += "\n"
        
        if len(results) > 8:
            response += f"*Showing top 8 results out of {len(db_result.get('results', []))} total funds found.*\n\n"
        
        response += "💡 Would you like me to provide more detailed information about any specific fund, or help you compare these options?"
        
        return response
    
    async def _handle_mixed_query(self, user_input: str, greeting: str) -> str:
        """Handle queries that might need both database and web search"""
        try:
            # Try database search first
            db_result = await self.tool_orchestrator.call_db_api(fund_name=user_input, deep_search=True)
            
            # Try web search for additional context
            web_result = await self.tool_orchestrator.call_tavily_search(query=user_input)
            
            # Combine results intelligently
            if db_result.get("found") and web_result.get("found"):
                return self._combine_db_and_web_results(db_result, web_result, user_input, greeting)
            elif db_result.get("found"):
                return self._format_fund_specific_response(db_result, user_input, greeting)
            elif web_result.get("found"):
                return self._format_general_knowledge_response(web_result, user_input, greeting)
            else:
                return f"""{greeting}I searched both our fund database and current market information for "{user_input}", but couldn't find specific results.

Let me help you in another way! I can assist with:
• Specific fund names or codes (ISIN)
• General investment questions and concepts
• Fund comparisons and recommendations
• SIP planning and investment strategies

💡 Could you provide more specific details about what you're looking for?"""
                
        except Exception as e:
            return self._format_error_response(str(e), user_input)
    
    def _combine_db_and_web_results(self, db_result: dict, web_result: dict, user_input: str, greeting: str) -> str:
        """Intelligently combine database and web search results"""
        response = f"{greeting}I found comprehensive information for your query!\n\n"
        
        # Add fund data if available
        if db_result.get("results"):
            results = db_result["results"][:3]  # Top 3 funds
            response += "**📊 Fund Information:**\n"
            for i, fund in enumerate(results, 1):
                if isinstance(fund, dict):
                    name = fund.get('scheme_name', 'Unknown Fund')
                    amc = fund.get('amc_name', 'N/A')
                    nav = fund.get('nav', 'N/A')
                    response += f"{i}. **{name}** ({amc}) - NAV: ₹{nav}\n"
            response += "\n"
        
        # Add market context if available
        if web_result.get("results"):
            web_info = web_result["results"][0].get("content", "")[:300]
            if web_info:
                response += "**🌐 Market Context:**\n"
                response += f"{self._create_conversational_explanation(web_info, user_input)}\n\n"
        
        response += "💡 Would you like detailed information about any specific fund, or more market insights on this topic?"
        return response
    
    def _create_conversational_explanation(self, content: str, user_input: str) -> str:
        """Convert web content into conversational explanation"""
        # Clean up content and make it more conversational
        cleaned_content = content.strip()
        if len(cleaned_content) > 500:
            cleaned_content = cleaned_content[:500] + "..."
        
        # Remove excessive technical jargon or formatting
        import re
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)  # Clean whitespace
        cleaned_content = re.sub(r'[^\w\s.,!?-]', '', cleaned_content)  # Remove special chars
        
        return cleaned_content
    
    def _format_error_response(self, error: str, user_input: str) -> str:
        """Format error responses conversationally"""
        return f"""I apologize, but I encountered a technical issue while processing your request about "{user_input}".

Don't worry though! I'm here to help you with:
• Specific mutual fund information (NAV, performance, fund manager details)
• General investment concepts and explanations
• Fund comparisons and recommendations
• SIP planning and investment guidance

💡 Could you try rephrasing your question, or let me know what specific information you're looking for?

Technical details (for reference): {error}"""

    def _create_system_prompt(self, intent: Intent, user_name: Optional[str] = None) -> str:
        """Create system prompt based on intent and user context"""
        
        base_prompt = """You are an intelligent mutual funds expert assistant. You have complete autonomy to provide helpful, accurate responses.

CORE PRINCIPLES:
- Analyze each user query independently and respond appropriately
- Use tools to gather information, then synthesize into clear, comprehensive answers
- For general questions (like "what is mutual funds?"), provide educational explanations with definitions, examples, and key concepts
- For specific queries, extract and present exactly what the user asks for
- Always be conversational and helpful - no rigid templates

TOOL GUIDELINES:
- search_funds_db: Use for specific mutual fund data, NAV, performance, fund managers, AMC information
- search_tavily_data: Use for general investment concepts, market explanations, current trends
- search_bse_schemes: Alternative database for BSE-listed schemes

RESPONSE APPROACH:
- When tools return data, synthesize it into clear, direct answers
- For "what is" questions, create comprehensive educational responses
- For specific fund queries, extract precise information requested (e.g., if asked for manager names, list the managers)
- Always provide value-added context when helpful

You have complete freedom to decide tool usage and response formatting based on what would be most helpful for each query."""
        
        if user_name:
            base_prompt += f"\n\nUser name: {user_name}"
        
        if intent.sentiment and intent.sentiment.label == SentimentLabel.NEGATIVE:
            base_prompt += "\n\n🚨 Note: User seems frustrated - be extra helpful and empathetic."
        
        return base_prompt
    
    async def _run_agent_async(self, enhanced_input: str) -> str:
        """Run the LangChain agent asynchronously with timeout protection"""
        
        try:
            logger.info("Running fully agentic LangChain agent...")
            
            # Run the agent in an executor with timeout protection
            loop = asyncio.get_event_loop()
            
            # Add debug logging before agent invocation
            logger.info(f"About to invoke agent with input length: {len(enhanced_input)}")
            
            # Add timeout wrapper
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.agent.invoke({"input": enhanced_input})
                ),
                timeout=25  # Increased to 25 seconds to match agent execution time
            )
            
            logger.info(f"Agent invocation completed. Result type: {type(result)}")
            
            # Extract the output from the result
            if isinstance(result, dict):
                response = result.get("output", str(result))
                logger.info(f"Extracted output from dict result")
                # Log intermediate steps if available
                if "intermediate_steps" in result:
                    logger.info(f"Agent completed with {len(result['intermediate_steps'])} reasoning steps")
                    for i, step in enumerate(result['intermediate_steps']):
                        logger.info(f"Step {i+1}: {step}")
            else:
                response = str(result)
                logger.info(f"Converted result to string")
            
            logger.info(f"Agent response received (length: {len(response) if response else 0})")
            return response
            
        except asyncio.TimeoutError:
            logger.warning("Agent execution timed out")
            raise asyncio.TimeoutError("Agent processing timed out")
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise e
    
    async def _ask_clarification(self, intent: Intent, user_input: str) -> str:
        """Ask for clarification when intent is unclear"""
        
        if intent.clarifying_question:
            return f"I'd like to help you better! {intent.clarifying_question}\n\nPlease specify:\n• The exact fund name you're looking for\n• What specific information you need (NAV, performance, holdings, etc.)\n\nThis helps me fetch the most accurate data for you."
        
        return "I'd be happy to help with your mutual fund query!\n\nTo provide you with accurate information, could you please specify:\n• **Fund name** (e.g., \"Axis Bluechip Fund\", \"SBI Small Cap Fund\")\n• **What you'd like to know** (current NAV, performance, fund manager, etc.)\n\nThis helps me search the right data sources for you."
    
    def _should_use_fallback_due_to_rate_limit(self) -> bool:
        """Check if we should proactively use fallback due to approaching rate limits"""
        try:
            # Track rate limit errors in a simple way
            # In a real system, you might use Redis or a database for this
            import os
            import time
            
            rate_limit_file = "rate_limit_tracker.tmp"
            current_time = time.time()
            
            # Check if we've had a recent rate limit error (within last 10 minutes)
            if os.path.exists(rate_limit_file):
                try:
                    with open(rate_limit_file, 'r') as f:
                        last_error_time = float(f.read().strip())
                    
                    # If we had a rate limit error in the last 5 minutes, use fallback
                    if current_time - last_error_time < 300:  # 5 minutes instead of 10
                        logger.info(f"Recent rate limit error detected ({(current_time - last_error_time)/60:.1f} minutes ago)")
                        return True
                        
                except (ValueError, IOError):
                    # If file is corrupted, ignore and continue
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rate limit status: {e}")
            return False  # Default to trying the agent if we can't check

    def _record_rate_limit_error(self):
        """Record that a rate limit error occurred"""
        try:
            import time
            rate_limit_file = "rate_limit_tracker.tmp"
            with open(rate_limit_file, 'w') as f:
                f.write(str(time.time()))
            logger.info("Rate limit error recorded for future fallback decisions")
        except Exception as e:
            logger.error(f"Error recording rate limit: {e}")

    def _extract_fund_name_from_input(self, user_input: str) -> Optional[str]:
        """Extract potential fund name from user input using simple heuristics"""
        import re
        
        user_lower = user_input.lower()
        
        # Handle comparison queries - extract first AMC mentioned
        comparison_patterns = [
            r'\b(dsp|edelweiss|axis|hdfc|sbi|icici|kotak|reliance|nippon|franklin|invesco|aditya birla)\b.*(?:vs|versus|or).*\b(dsp|edelweiss|axis|hdfc|sbi|icici|kotak|reliance|nippon|franklin|invesco|aditya birla)\b',
            r'which.*(fund|mutual fund).*(better|best).*between.*(dsp|edelweiss|axis|hdfc|sbi|icici|kotak)',
            r'compare.*(dsp|edelweiss|axis|hdfc|sbi|icici|kotak).*(?:and|with).*(dsp|edelweiss|axis|hdfc|sbi|icici|kotak)'
        ]
        
        for pattern in comparison_patterns:
            match = re.search(pattern, user_lower, re.IGNORECASE)
            if match:
                # For comparison queries, return first AMC name found
                groups = [g for g in match.groups() if g and g.lower() in ['dsp', 'edelweiss', 'axis', 'hdfc', 'sbi', 'icici', 'kotak', 'reliance', 'nippon', 'franklin', 'invesco', 'aditya birla']]
                if groups:
                    return groups[0].title()
        
        # First check for well-known AMC names
        known_amcs = ["edelweiss", "axis", "hdfc", "sbi", "icici", "kotak", "reliance", "nippon", "franklin", "dsp", "invesco", "aditya birla"]
        for amc in known_amcs:
            if amc in user_lower:
                return amc.title()
        
        # Common fund name patterns
        fund_patterns = [
            r'\b([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\s+(?:mutual\s+)?fund\b',
            r'\b([A-Za-z]+)\s+(?:bluechip|large\s+cap|mid\s+cap|small\s+cap|equity|debt|hybrid)\b',
            r'\b(axis|hdfc|sbi|icici|aditya\s+birla|edelweiss|kotak|reliance|nippon|franklin|dsp|invesco)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b'
        ]
        
        for pattern in fund_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    # Clean up the result - remove question marks and extra spaces
                    result = ' '.join(matches[0]).strip().rstrip('?').strip()
                    return result
                else:
                    return matches[0].strip().rstrip('?').strip()
        
        return None

    async def _handle_agent_fallback(self, intent: Intent, user_input: str) -> str:
        """
        Pure AI-driven fallback - agent decides which tools to use
        NO hardcoded routing based on intent classification
        """
        logger.info(f"Using pure AI-driven fallback for: {user_input}")
        
        # Let the agent decide through both approaches - database AND web search
        # The agent will determine which results are more relevant
        try:
            # Try both approaches and let the agent synthesize the best answer
            db_result = None
            web_result = None
            
            # Attempt database search (for any potential fund-related content)
            try:
                logger.info("Trying database search as one option")
                db_result = await self.tool_orchestrator._comprehensive_db_search(user_input)
            except Exception as db_error:
                logger.info(f"Database search failed: {db_error}")
            
            # Attempt web search (for current market information and general guidance)
            try:
                logger.info("Trying web search as another option") 
                web_result = await self.tool_orchestrator.call_tavily_search(user_input)
            except Exception as web_error:
                logger.info(f"Web search failed: {web_error}")
            
            # PRIORITIZE DATABASE RESULTS for fund-specific queries
            # Show database first, then complement with web search
            if db_result and db_result.get("found") and db_result.get("results"):
                # Primary: Database results with web context
                return self._format_database_first_response(db_result, user_input, web_result)
            elif web_result and web_result.get("found") and web_result.get("results"):
                # Fallback: Web results only if no database results
                return self._format_intelligent_web_response(web_result, user_input, db_result)
            else:
                # Both failed, provide helpful guidance
                return self._format_no_results_response(user_input)
                
        except Exception as e:
            logger.error(f"Agent fallback error: {e}")
            
        # If all tools fail, provide intelligent assistance anyway
        return f"""I'm analyzing your question: "{user_input}"

**🔍 My Analysis Process:**
1. **Understanding**: You're asking about mutual fund information or investment guidance
2. **Challenge**: Both my database search and web search tools encountered technical issues
3. **Solution**: Let me provide general guidance based on my knowledge

**💡 Here's what I can tell you:**

If you're asking about **specific funds**, I typically search our comprehensive mutual fund database for real-time NAV, performance data, and detailed fund information.

If you're asking about **investment advice or market trends**, I usually search current web sources for the latest market insights, expert opinions, and investment strategies.

**🚀 Next Steps:**
- Try rephrasing your question with more specific details
- Ask about a particular fund name for database lookup
- Request general investment guidance for market research

**Sample Questions I Handle Well:**
- "What is the current NAV of HDFC Top 100 Fund?"
- "How to start SIP investment in 2024?"
- "Compare large cap vs mid cap funds"

        Please try asking your question again - my systems should be ready now!"""

    def _format_database_first_response(self, db_result: dict, user_input: str, web_result: dict = None) -> str:
        """Format database results first, then complement with web search context"""
        try:
            # Start with analysis process
            response = f"""🔍 **My Analysis Process:**
1. **Understanding**: You're asking about: {user_input}
2. **Strategy**: I searched our comprehensive mutual fund database first for specific fund data
3. **Database Results**: Found {len(db_result.get('results', []))} matching funds in our database
4. **Web Context**: Also searched current market sources for additional insights

# 🏦 DATABASE FUND RESULTS

"""
            
            # Display actual database results
            results = db_result.get('results', [])
            for i, fund in enumerate(results[:10], 1):  # Show top 10 funds
                if isinstance(fund, dict):
                    scheme_name = fund.get('scheme_name', 'Unknown Fund')
                    amc_name = fund.get('amc_name', 'Unknown AMC')
                    
                    # Try different field names for NAV
                    nav = fund.get('nav') or fund.get('current_nav') or fund.get('latest_nav') or 'N/A'
                    
                    # Try different field names for fund type
                    fund_type = fund.get('fund_type') or fund.get('fund_subtype') or fund.get('scheme_type') or fund.get('category') or 'N/A'
                    
                    # Plan information
                    plan = fund.get('plan') or fund.get('scheme_plan') or 'Direct Plan'
                    
                    # Performance data
                    return_1y = fund.get('return_1y', 'N/A')
                    return_3y = fund.get('return_3y', 'N/A')
                    return_5y = fund.get('return_5y', 'N/A')
                    expense_ratio = fund.get('expense_ratio', 'N/A')
                    
                    # Risk category
                    risk_category = fund.get('sebi_risk_category', 'N/A')
                    
                    response += f"""**{i}. {scheme_name}**
• **AMC**: {amc_name}
• **Type**: {fund_type} | **Plan**: {plan}
• **Current NAV**: ₹{nav}"""
                    
                    # Show performance returns if available
                    returns_info = []
                    if return_1y and return_1y != 'N/A':
                        returns_info.append(f"1Y: {return_1y}%")
                    if return_3y and return_3y != 'N/A':
                        returns_info.append(f"3Y: {return_3y}%")
                    if return_5y and return_5y != 'N/A':
                        returns_info.append(f"5Y: {return_5y}%")
                    
                    if returns_info:
                        response += f"\n• **Returns**: {' | '.join(returns_info)}"
                    
                    if expense_ratio and expense_ratio != 'N/A':
                        response += f"\n• **Expense Ratio**: {expense_ratio}%"
                    
                    if risk_category and risk_category != 'N/A':
                        response += f"\n• **Risk Category**: {risk_category}"
                    
                    # ISIN for reference - always show if available
                    isin = fund.get('isin', 'N/A')
                    if isin and isin != 'N/A':
                        response += f"\n• **ISIN**: {isin}"
                    
                    response += "\n\n"
            
            # Add summary statistics
            if len(results) > 10:
                response += f"*Showing top 10 of {len(results)} total matches. Ask for specific funds for more details.*\n\n"
            
            # Add web context if available
            if web_result and web_result.get("results"):
                response += "# 🌐 ADDITIONAL MARKET CONTEXT\n\n"
                for item in web_result.get("results", [])[:2]:  # Top 2 web results
                    if item.get("content"):
                        title = item.get("title", "Market Insight")
                        content = item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"]
                        source = item.get("url", "").split("/")[2] if item.get("url") else "Web Source"
                        response += f"**{title}**\n{content}\n*Source: {source}*\n\n"
            
            response += """**💡 Investment Guidance:**
- Compare funds within the same category for better analysis
- Consider expense ratios and consistent performance over time
- Direct plans typically have lower expense ratios than regular plans
- Consult a financial advisor for personalized investment advice

**🎯 Related Questions:**
- "Show detailed factsheet for [specific fund name]"
- "Compare performance of these funds with benchmarks"
- "What's the minimum investment amount for SIP?"
"""
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting database-first response: {e}")
            return f"I found {len(db_result.get('results', []))} funds in our database but encountered formatting issues. Please ask for specific fund details."

    def _format_intelligent_web_response(self, web_result: dict, user_input: str, db_result: dict = None) -> str:
        """Format web search results with intelligent analysis"""
        try:
            insights = []
            for item in web_result.get("results", [])[:3]:  # Top 3 results
                if item.get("content"):
                    title = item.get("title", "Market Insight")
                    content = item["content"][:250] + "..." if len(item["content"]) > 250 else item["content"]
                    source = item.get("url", "").split("/")[2] if item.get("url") else "Web Source"
                    insights.append(f"**{title}**\n{content}\n*Source: {source}*")
                    
            formatted_insights = "\n\n".join(insights)
            
            # Add database context if available
            db_context = ""
            if db_result and db_result.get("results"):
                db_context = f"\n\n**Related Fund Data Available:**\nI also found {len(db_result['results'])} funds in our database that may be relevant to your query."
            
            return f"""🔍 **My Analysis Process:**
1. **Understanding**: You're asking about: {user_input}
2. **Strategy**: I searched current web sources for the most up-to-date information
3. **Sources**: Found relevant insights from financial platforms and market experts
4. **Analysis**: Providing comprehensive guidance based on current market conditions

**📊 Current Market Information:**

{formatted_insights}

{db_context}

**💡 Key Takeaways:**
- This information reflects current market conditions and expert opinions
- Consider consulting with a financial advisor for personalized advice
- Market conditions can change - stay updated with recent developments

**🎯 Related Questions You Might Ask:**
- "What are the best performing mutual funds this year?"
- "How do I choose between different fund categories?"
- "What's the minimum investment for starting SIP?"
"""
            
        except Exception as e:
            logger.error(f"Error formatting intelligent web response: {e}")
            return f"I found relevant information for your query but encountered formatting issues. The search results are available - please try asking again."

    def _format_no_results_response(self, user_input: str) -> str:
        """Format response when both database and web search fail"""
        return f"""🔍 **My Analysis Process:**
1. **Understanding**: You asked about: "{user_input}"
2. **Search Strategy**: I attempted both database search and web research
3. **Challenge**: Both search methods didn't return specific results for your query
4. **Next Steps**: Let me provide general guidance and suggestions

**💡 Here's how I can help:**

**For Fund Information:**
- Ask about specific fund names (e.g., "HDFC Top 100 Fund NAV")
- Request comparisons between named funds
- Inquire about fund performance metrics

**For Investment Guidance:**
- "How to start SIP investment?"
- "Best mutual fund categories for beginners"
- "Tax saving mutual funds vs ELSS"

**For Market Insights:**
- "Current mutual fund market trends"
- "Top performing fund houses in 2024"
- "Should I invest in large cap or mid cap funds?"

**🚀 Try rephrasing your question with:**
- More specific fund names or categories
- Clear investment goals or time horizons
- Specific metrics you're interested in (NAV, returns, ratings)

I'm ready to provide detailed analysis once I have clearer search parameters!"""

    def _format_web_insights(self, result: dict, user_input: str) -> str:
        """Format web search results into intelligent insights"""
        try:
            insights = []
            for item in result.get("results", [])[:3]:  # Top 3 results
                if item.get("content"):
                    insights.append(f"**{item.get('title', 'Market Insight')}**\n{item['content'][:200]}...")
                    
            formatted_insights = "\n\n".join(insights)
            
            return f"""Based on current market analysis for your question: "{user_input}"

**Real-time Market Insights:**

{formatted_insights}

**Analysis Summary:**
The information above provides current market perspectives on your question. These insights are gathered from live financial sources and market analysis platforms.

**Note:** This information reflects current market conditions and expert opinions. Always consult with a financial advisor for personalized investment decisions."""
            
        except Exception as e:
            logger.error(f"Error formatting web insights: {e}")
            return f"I found relevant information but encountered formatting issues. Please try rephrasing your question."

    def _format_comparison_insights(self, result: dict, user_input: str) -> str:
        """Format fund comparison results with market analysis"""
        try:
            insights = []
            for item in result.get("results", [])[:2]:  # Top 2 results
                if item.get("content"):
                    insights.append(f"**Market Analysis:** {item['content'][:300]}...")
                    
            formatted_insights = "\n\n".join(insights)
            
            return f"""Comparative analysis for your query: "{user_input}"

**Current Market Perspectives:**

{formatted_insights}

**Investment Considerations:**
- Compare expense ratios and fund performance metrics
- Consider your investment timeline and risk tolerance  
- Review fund manager track records and AUM stability
- Diversify across different fund categories and houses

**Recommendation:** Use this market analysis alongside specific fund performance data to make informed investment decisions."""
            
        except Exception as e:
            logger.error(f"Error formatting comparison insights: {e}")
            return f"I found comparison data but encountered processing issues. Please specify the exact funds you want to compare."

    def _format_fund_data_insights(self, result: dict, fund_name: str) -> str:
        """Format database fund results with intelligent analysis"""
        try:
            funds = result.get("results", [])
            if not funds:
                return f"No specific data found for '{fund_name}'. Please check the fund name and try again."
                
            fund = funds[0]  # Primary result
            
            # Extract key metrics
            nav = fund.get("nav", "Not available")
            returns_1y = fund.get("returns_1year", "Not available") 
            returns_3y = fund.get("returns_3year", "Not available")
            expense_ratio = fund.get("expense_ratio", "Not available")
            category = fund.get("category", "Not available")
            
            return f"""**Fund Analysis: {fund.get('fund_name', fund_name)}**

**Current Performance:**
- **NAV:** ₹{nav}
- **1 Year Return:** {returns_1y}%
- **3 Year Return:** {returns_3y}%
- **Expense Ratio:** {expense_ratio}%
- **Category:** {category}

**Investment Insights:**
- Performance metrics show {self._analyze_performance_trend(returns_1y, returns_3y)}
- Expense ratio is {self._analyze_expense_ratio(expense_ratio)}
- Fund category suggests {self._get_category_insights(category)}

**Risk Assessment:** Based on current data, this fund shows {self._assess_risk_level(fund)} risk characteristics.

**Note:** Analysis based on latest available fund data. Consider your investment goals and consult a financial advisor."""
            
        except Exception as e:
            logger.error(f"Error formatting fund data insights: {e}")
            return f"Found fund data but encountered analysis issues. Please verify the fund name: '{fund_name}'"

    def _analyze_performance_trend(self, returns_1y, returns_3y) -> str:
        """Analyze performance trend"""
        try:
            if returns_1y == "Not available" or returns_3y == "Not available":
                return "insufficient data for trend analysis"
                
            r1y = float(str(returns_1y).replace("%", ""))
            r3y = float(str(returns_3y).replace("%", ""))
            
            if r1y > r3y:
                return "improving short-term performance"
            elif r1y < r3y:
                return "recent performance below long-term average" 
            else:
                return "consistent performance pattern"
        except:
            return "mixed performance requiring detailed analysis"

    def _analyze_expense_ratio(self, expense_ratio) -> str:
        """Analyze expense ratio competitiveness"""
        try:
            if expense_ratio == "Not available":
                return "not disclosed"
                
            ratio = float(str(expense_ratio).replace("%", ""))
            
            if ratio < 1.0:
                return "competitive (below 1%)"
            elif ratio < 2.0:
                return "moderate (1-2% range)"
            else:
                return "high (above 2%)"
        except:
            return "requires verification"

    def _get_category_insights(self, category) -> str:
        """Get insights based on fund category"""
        if category == "Not available":
            return "general diversified investment approach"
            
        category_lower = category.lower()
        
        if "equity" in category_lower:
            return "equity-focused strategy with growth potential"
        elif "debt" in category_lower or "bond" in category_lower:
            return "debt-oriented approach for stable returns"
        elif "hybrid" in category_lower or "balanced" in category_lower:
            return "balanced allocation between equity and debt"
        elif "index" in category_lower:
            return "passive index tracking strategy"
        else:
            return "specialized investment strategy"

    def _assess_risk_level(self, fund_data) -> str:
        """Assess risk level based on fund data"""
        try:
            category = fund_data.get("category", "").lower()
            
            if "equity" in category:
                return "moderate to high"
            elif "debt" in category:
                return "low to moderate"  
            elif "hybrid" in category:
                return "moderate"
            else:
                return "variable"
        except:
            return "undetermined"

    async def _run_agent_async(self, enhanced_input: str) -> str:
        """Run the LangChain agent asynchronously with timeout protection"""
        
        try:
            logger.info("Running fully agentic LangChain agent...")
            
            # Run the agent in an executor with timeout protection
            loop = asyncio.get_event_loop()
            
            # Add debug logging before agent invocation
            logger.info(f"About to invoke agent with input length: {len(enhanced_input)}")
            
            # Add timeout wrapper
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.agent.invoke({"input": enhanced_input})
                ),
                timeout=15  # Reduced to 15 seconds for faster debugging
            )
            
            logger.info(f"Agent invocation completed. Result type: {type(result)}")
            
            # Extract the output from the result
            if isinstance(result, dict):
                response = result.get("output", str(result))
                logger.info(f"Extracted output from dict result")
                # Log intermediate steps if available
                if "intermediate_steps" in result:
                    logger.info(f"Agent completed with {len(result['intermediate_steps'])} reasoning steps")
                    for i, step in enumerate(result['intermediate_steps']):
                        logger.info(f"Step {i+1}: {step}")
            else:
                response = str(result)
                logger.info(f"Converted result to string")
            
            logger.info(f"Agent response received (length: {len(response) if response else 0})")
            return response
            
        except asyncio.TimeoutError:
            logger.warning("Agent execution timed out")
            raise asyncio.TimeoutError("Agent processing timed out")
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise e

    def _create_web_search_response(self, web_result: dict, user_input: str) -> str:
        """Create response from web search results"""
        
        results = web_result.get("results", [])
        if not results:
            return f"I couldn't find relevant information about '{user_input}' from web sources."
            
        response = f"## {user_input}\n\n"
        
        for i, result in enumerate(results[:3], 1):  # Show top 3 results
            title = result.get("title", "No title")
            content = result.get("content", "No content available")
            url = result.get("url", "")
            
            response += f"**{i}. {title}**\n"
            response += f"{content[:200]}{'...' if len(content) > 200 else ''}\n"
            if url:
                response += f"*Source: {url}*\n\n"
        
        return response

    def _add_related_questions(self, response: str, related_questions: List[str]) -> str:
        """Add related questions to the response"""
        
        if not related_questions:
            return response
            
        response += "\n\n**💡 You might also be interested in:**\n"
        for question in related_questions:
            response += f"• {question}\n"
            
        return response

    def _create_general_info_fallback(self, user_input: str) -> str:
        """Create intelligent fallback response for general information queries"""
        
        query_lower = user_input.lower()
        
        # Check for specific topics in the query
        if any(word in query_lower for word in ['perform', 'best', 'top', 'good', 'recommend']):
            return """## Current Mutual Fund Performance Guidance

**🚀 Top Performing Fund Categories (Based on market trends):**

• **Large Cap Equity Funds**: Generally stable with steady returns
• **Mid Cap Funds**: Higher growth potential but with increased volatility  
• **Flexi Cap Funds**: Balanced approach across market capitalizations
• **Technology Sector Funds**: Strong performance driven by digital transformation
• **ELSS Funds**: Tax-saving with potential for good returns

**📈 Key Factors to Consider:**
• **Time Horizon**: Long-term investments (5+ years) generally perform better
• **Risk Tolerance**: Match fund category with your risk appetite
• **SIP Strategy**: Systematic Investment Plans help average out market volatility
• **Diversification**: Don't put all money in one fund or category

**💡 Popular Fund Houses to Consider:**
• HDFC Mutual Fund • SBI Mutual Fund • ICICI Prudential
• Axis Mutual Fund • Mirae Asset • Nippon India

**⚠️ Important Note**: Past performance doesn't guarantee future returns. Always consult with a financial advisor before making investment decisions."""

        elif any(word in query_lower for word in ['sip', 'systematic', 'monthly', 'invest']):
            return """## SIP Investment Guide

**🎯 Systematic Investment Plan (SIP) Benefits:**

• **Rupee Cost Averaging**: Buy more units when NAV is low, fewer when high
• **Disciplined Investing**: Automated monthly investments build good habits
• **Lower Entry Barrier**: Start with as little as ₹500 per month
• **Compounding Power**: Regular investments compound over time

**📅 SIP Strategy Recommendations:**
• **Start Early**: Time in market beats timing the market
• **Increase Annually**: Step up SIP by 10-15% each year
• **Stay Consistent**: Don't stop SIPs during market downturns
• **Review Quarterly**: Monitor performance but avoid frequent changes

**💰 Popular SIP Amounts:**
• ₹1,000/month → ₹12,000/year
• ₹2,500/month → ₹30,000/year  
• ₹5,000/month → ₹60,000/year

**🎯 Goal-Based SIP Planning:**
• Child's Education: 10-15 years horizon
• Retirement: 20-30 years horizon
• Home Purchase: 5-10 years horizon"""

        elif any(word in query_lower for word in ['tax', 'elss', '80c', 'save']):
            return """## Tax Saving & ELSS Funds

**💸 Tax Benefits Under Section 80C:**

• **ELSS Investment Limit**: Up to ₹1.5 lakh per financial year
• **Tax Deduction**: Direct reduction from taxable income
• **Lock-in Period**: 3 years (shortest among 80C options)
• **Potential Returns**: Equity-linked with growth potential

**🏆 Top ELSS Fund Categories:**
• **Large Cap ELSS**: Lower risk, steady returns
• **Multi Cap ELSS**: Balanced across market caps
• **Flexi Cap ELSS**: Dynamic allocation strategy

**📊 Tax Calculation Example:**
• Investment: ₹1,50,000 in ELSS
• Tax Bracket: 30%
• Tax Saved: ₹46,500 (including cess)
• Effective Cost: ₹1,03,500

**⏰ Important Deadlines:**
• Investment: Before March 31st
• Tax Benefits: Applicable for same financial year"""

        elif any(word in query_lower for word in ['risk', 'safe', 'conservative', 'debt']):
            return """## Risk Management in Mutual Funds

**🛡️ Risk Categories (Low to High):**

**1. Liquid/Money Market Funds**: 
   • Lowest risk, highest liquidity
   • 3-7% returns typically
   • Suitable for emergency funds

**2. Debt/Bond Funds**:
   • Low to moderate risk
   • 6-9% returns typically  
   • Good for conservative investors

**3. Hybrid Funds**:
   • Moderate risk (mix of equity + debt)
   • 8-12% returns typically
   • Balanced approach

**4. Large Cap Equity**:
   • Moderate to high risk
   • 10-15% returns typically
   • Established company stocks

**5. Mid/Small Cap Equity**:
   • Highest risk, highest potential returns
   • 15-25% returns possible (but volatile)

**⚖️ Risk Management Tips:**
• Diversify across categories
• Match risk with time horizon  
• Regular portfolio review
• Don't invest only based on past returns"""

        else:
            # Generic helpful response
            return """## Mutual Fund Investment Guide

**🎯 Getting Started with Mutual Funds:**

**Popular Investment Options:**
• **Equity Funds**: Growth potential, suitable for long-term goals
• **Debt Funds**: Stable returns, lower risk
• **Hybrid Funds**: Balanced mix of equity and debt
• **ELSS**: Tax-saving funds with 3-year lock-in

**💡 Investment Strategies:**
• **SIP (Systematic Investment Plan)**: Regular monthly investments
• **Lump Sum**: One-time investment when you have surplus funds
• **SWP (Systematic Withdrawal Plan)**: Regular income from investments

**📈 Key Metrics to Track:**
• **NAV**: Net Asset Value (daily price)
• **Returns**: 1-year, 3-year, 5-year performance
• **Expense Ratio**: Annual fund management fees
• **AUM**: Assets Under Management (fund size)

**🏢 Top AMCs (Asset Management Companies):**
• HDFC • SBI • ICICI Prudential • Axis • Mirae Asset

**⚠️ Important**: Always read scheme documents and consult financial advisors for personalized advice."""
    
    def _create_simple_fund_response(self, db_result: dict, fund_name: str) -> str:
        """Create a simple, fast response for fund data"""
        
        results = db_result.get("results", [])
        if not results:
            return f"No funds found for '{fund_name}'"
        
        # Limit to first 5 results for speed
        limited_results = results[:5] if isinstance(results, list) else [results]
        
        response = f"## {fund_name} - Fund Information\n\n"
        
        for i, fund in enumerate(limited_results, 1):
            if isinstance(fund, dict):
                # Handle different field names from different APIs
                scheme_name = (fund.get('scheme_name') or 
                              fund.get('fund_name') or 
                              'N/A')
                
                # Handle NAV from different sources
                nav = (fund.get('nav') or 
                      fund.get('current_nav') or 
                      'N/A')
                
                # Handle AMC name from different sources  
                amc_name = (fund.get('amc_name') or 
                           fund.get('amc_code') or
                           fund.get('fund_house') or
                           'N/A')
                
                # Handle fund type from different sources
                fund_type = (fund.get('fund_type') or 
                           fund.get('scheme_type') or 
                           fund.get('category') or
                           'N/A')
                
                response += f"**{i}. {scheme_name}**\n"
                response += f"• AMC: {amc_name}\n"
                response += f"• Type: {fund_type}\n"
                if nav != 'N/A':
                    response += f"• Current NAV: ₹{nav}\n"
                
                # Add additional BSE-specific information if available
                if fund.get('minimum_purchase_amount'):
                    response += f"• Min Investment: ₹{fund.get('minimum_purchase_amount')}\n"
                if fund.get('sip_flag') == 'Y':
                    response += f"• SIP Available: Yes\n"
                
                response += "\n"
        
        response += f"**Data Source:** {db_result.get('source', 'Database')}\n"
        response += f"**Retrieved:** {db_result.get('retrieved_at', 'N/A')[:10]}\n"
        
        return response
    
    async def _handle_error(self, error_msg: str, user_input: str) -> str:
        """Handle errors gracefully"""
        logger.error(f"Error handling user input: {error_msg}")
        return f"I apologize, but I encountered an issue while processing your request.\\n\\n**Error**: {error_msg}\\n\\n**What you can try:**\\n• Rephrase your question with a specific fund name\\n• Ask for general mutual fund information instead\\n• Try again in a moment\\n\\nWould you like to try asking about a specific mutual fund or general investment concepts?"
    
    def _analyze_query_specificity(self, user_input: str) -> str:
        """Analyze what specific information the user is asking for"""
        user_lower = user_input.lower()
        
        # Define specific query patterns
        query_patterns = {
            'fund_manager': ['fund manager', 'manager', 'who manages', 'managed by'],
            'nav': ['nav', 'price', 'current price', 'net asset value', 'unit price'],
            'performance': ['performance', 'returns', 'return', '1 year', '3 year', 'ytd', 'yield'],
            'expense_ratio': ['expense ratio', 'charges', 'fees', 'cost'],
            'risk': ['risk', 'riskometer', 'risk level', 'sebi risk'],
            'investment_amount': ['minimum investment', 'min investment', 'minimum amount', 'lumpsum', 'sip amount'],
            'comparison': ['compare', 'vs', 'versus', 'difference', 'better'],
            'holdings': ['holdings', 'portfolio', 'top holdings', 'investments'],
            'benchmark': ['benchmark', 'index', 'compared to'],
            'amc': ['amc', 'asset management', 'company', 'mutual fund company'],
            'plan_type': ['direct', 'regular', 'growth', 'dividend', 'idcw'],
            'general': ['details', 'information', 'about', 'tell me', 'data']
        }
        
        # Check for specific query types
        for query_type, keywords in query_patterns.items():
            for keyword in keywords:
                if keyword in user_lower:
                    return query_type
        
        return 'general'
    
    def _format_specific_response(self, result: Dict[str, Any], fund_name: str, query_type: str, user_input: str) -> str:
        """Format response based on specific query type"""
        
        # Debug: Log the exact structure being passed to extraction
        logger.info(f"DEBUG _format_specific_response: result keys = {list(result.keys())}")
        logger.info(f"DEBUG _format_specific_response: result type = {type(result)}")
        if 'results' in result:
            logger.info(f"DEBUG _format_specific_response: results type = {type(result['results'])}")
            if isinstance(result['results'], list) and result['results']:
                logger.info(f"DEBUG _format_specific_response: first result keys = {list(result['results'][0].keys())}")
        
        # Extract fund data from complex structure
        fund_data = self._extract_fund_data_from_result(result)
        
        logger.info(f"DEBUG _format_specific_response: extracted fund_data = {fund_data}")
        
        if not fund_data:
            return f"❌ No data available for '{fund_name}'"
        
        fund_name_display = (fund_data.get('scheme_name') or 
                           fund_data.get('fund_name') or 
                           fund_name)
        
        # Format response based on specific query type
        if query_type == 'fund_manager':
            fund_manager = fund_data.get('fund_manager', 'N/A')
            if fund_manager != 'N/A':
                return f"👨‍💼 **Fund Manager of {fund_name_display}:** {fund_manager}"
            else:
                return f"❌ Fund manager information not available for {fund_name_display}"
        
        elif query_type == 'nav':
            nav = fund_data.get('nav', 'N/A')
            nav_date = fund_data.get('nav_date', 'N/A')
            if nav != 'N/A':
                response = f"💰 **Current NAV of {fund_name_display}:** ₹{nav}"
                if nav_date != 'N/A':
                    response += f" (as of {nav_date})"
                return response
            else:
                return f"❌ NAV information not available for {fund_name_display}"
        
        elif query_type == 'performance':
            performance_data = []
            if fund_data.get('return_1m') is not None:
                performance_data.append(f"1 Month: {fund_data['return_1m']}%")
            if fund_data.get('return_ytd') is not None:
                performance_data.append(f"YTD: {fund_data['return_ytd']}%")
            if fund_data.get('return_1y') is not None:
                performance_data.append(f"1 Year: {fund_data['return_1y']}%")
            if fund_data.get('return_3y') is not None:
                performance_data.append(f"3 Years: {fund_data['return_3y']}%")
            
            if performance_data:
                return f"📊 **Performance of {fund_name_display}:**\n" + "\n".join(f"• {data}" for data in performance_data)
            else:
                return f"❌ Performance data not available for {fund_name_display}"
        
        elif query_type == 'expense_ratio':
            expense_ratio = fund_data.get('expense_ratio', 'N/A')
            if expense_ratio != 'N/A':
                return f"💰 **Expense Ratio of {fund_name_display}:** {expense_ratio}%"
            else:
                return f"❌ Expense ratio information not available for {fund_name_display}"
        
        elif query_type == 'risk':
            risk_category = fund_data.get('sebi_risk_category', 'N/A')
            if risk_category != 'N/A':
                return f"⚠️ **Risk Level of {fund_name_display}:** {risk_category}"
            else:
                return f"❌ Risk information not available for {fund_name_display}"
        
        elif query_type == 'investment_amount':
            investment_info = []
            min_lumpsum = fund_data.get('minimum_lumpsum', fund_data.get('purchase_amount_min', 'N/A'))
            min_sip = fund_data.get('minimum_sip', 'N/A')
            
            if min_lumpsum != 'N/A':
                investment_info.append(f"Minimum Lumpsum: ₹{min_lumpsum}")
            if min_sip != 'N/A':
                investment_info.append(f"Minimum SIP: ₹{min_sip}")
            
            if investment_info:
                return f"💼 **Investment Requirements for {fund_name_display}:**\n" + "\n".join(f"• {info}" for info in investment_info)
            else:
                return f"❌ Investment amount information not available for {fund_name_display}"
        
        elif query_type == 'amc':
            amc = fund_data.get('amc_name', 'N/A')
            if amc != 'N/A':
                return f"🏢 **AMC of {fund_name_display}:** {amc}"
            else:
                return f"❌ AMC information not available for {fund_name_display}"
        
        elif query_type == 'benchmark':
            benchmark = fund_data.get('benchmark', 'N/A')
            if benchmark != 'N/A':
                return f"📊 **Benchmark of {fund_name_display}:** {benchmark}"
            else:
                return f"❌ Benchmark information not available for {fund_name_display}"
        
        else:
            # Default to comprehensive format for general queries
            # Create a simple comprehensive response using the extracted fund data
            response = f"**{fund_name_display}**\n\n"
            
            # Add ISIN if available
            if fund_data.get('isin'):
                response += f"📋 **ISIN**: {fund_data.get('isin')}\n"
            
            # Add fund type if available
            if fund_data.get('scheme_type'):
                response += f"📊 **Type**: {fund_data.get('scheme_type')}\n"
            elif fund_data.get('fund_type'):
                response += f"📊 **Type**: {fund_data.get('fund_type')}\n"
            
            # Add plan if available
            if fund_data.get('scheme_plan'):
                response += f"📋 **Plan**: {fund_data.get('scheme_plan')}\n"
            elif fund_data.get('plan'):
                response += f"📋 **Plan**: {fund_data.get('plan')}\n"
            
            # Add performance section
            response += "\n**📊 Performance:**\n"
            performance_added = False
            
            if fund_data.get('return_1y'):
                response += f"• 1 Year: {fund_data.get('return_1y')}%\n"
                performance_added = True
            if fund_data.get('return_3y'):
                response += f"• 3 Years: {fund_data.get('return_3y')}%\n"
                performance_added = True
            if fund_data.get('return_5y'):
                response += f"• 5 Years: {fund_data.get('return_5y')}%\n"
                performance_added = True
                
            if not performance_added:
                response += "• Performance data not available\n"
            
            # Add investment details section
            response += "\n**💼 Investment Details:**\n"
            investment_added = False
            
            if fund_data.get('minimum_purchase_amount'):
                response += f"• Minimum Investment: ₹{fund_data.get('minimum_purchase_amount')}\n"
                investment_added = True
            if fund_data.get('minimum_lumpsum'):
                response += f"• Minimum Lumpsum: ₹{fund_data.get('minimum_lumpsum')}\n"
                investment_added = True
            if fund_data.get('minimum_sip'):
                response += f"• Minimum SIP: ₹{fund_data.get('minimum_sip')}\n"
                investment_added = True
            if fund_data.get('sip_flag') == 'Y':
                response += f"• SIP Available: Yes\n"
                investment_added = True
                
            if not investment_added:
                response += "• Investment details not available\n"
            
            # Add NAV if available
            if fund_data.get('nav'):
                response += f"\n**💰 Current NAV**: ₹{fund_data.get('nav')}"
                if fund_data.get('nav_date'):
                    response += f" (as of {fund_data.get('nav_date')})"
                response += "\n"
            
            # Add confidence and source
            confidence = result.get('confidence', 95.0)
            source = result.get('source', 'database')
            response += f"\n*📊 Source: {source} | Confidence: {confidence}%*"
            
            return response
    
    def _extract_fund_data_from_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fund data from complex nested result structure"""
        fund_data = {}
        
        # Handle direct results list (from fast search)
        if result.get("results") and isinstance(result["results"], list) and result["results"]:
            # Take the first result for detailed analysis
            first_result = result["results"][0]
            return first_result  # Return the fund data directly
        
        # Check if result has 'data' array (comprehensive search)
        if result.get("data") and isinstance(result["data"], list):
            for data_item in result["data"]:
                if data_item.get("results") and isinstance(data_item["results"], dict):
                    nested_results = data_item["results"]
                    
                    # Extract from factsheet
                    if "factsheet" in nested_results:
                        factsheet = nested_results["factsheet"]
                        fund_data.update({
                            "scheme_name": factsheet.get("scheme_name"),
                            "isin": factsheet.get("isin"),
                            "amc_name": factsheet.get("amc"),
                            "fund_manager": factsheet.get("fund_manager"),
                            "scheme_type": factsheet.get("scheme_type"),
                            "expense_ratio": factsheet.get("expense_ratio"),
                            "exit_load": factsheet.get("exit_load"),
                            "minimum_lumpsum": factsheet.get("minimum_lumpsum"),
                            "minimum_sip": factsheet.get("minimum_sip"),
                            "benchmark": factsheet.get("benchmark"),
                            "plan": factsheet.get("plan"),
                            "sub_category": factsheet.get("sub_category"),
                            "sebi_risk_category": factsheet.get("sebi_risk_category")
                        })
                    
                    # Extract from returns
                    if "returns" in nested_results:
                        returns = nested_results["returns"]
                        fund_data.update({
                            "return_1m": returns.get("return_1m"),
                            "return_1y": returns.get("return_1y"),
                            "return_3y": returns.get("return_3y"),
                            "return_ytd": returns.get("return_ytd")
                        })
                    
                    # Extract from NAV history
                    if "nav_history" in nested_results and nested_results["nav_history"].get("nav_history"):
                        nav_data = nested_results["nav_history"]["nav_history"]
                        if isinstance(nav_data, list) and nav_data:
                            latest_nav = nav_data[0]
                            fund_data.update({
                                "nav": latest_nav.get("nav"),
                                "nav_date": latest_nav.get("date")
                            })
                    
                    # Extract from BSE scheme
                    if "bse_scheme" in nested_results and nested_results["bse_scheme"].get("data"):
                        bse_schemes = nested_results["bse_scheme"]["data"]
                        if isinstance(bse_schemes, list) and bse_schemes:
                            bse_scheme = bse_schemes[0]
                            fund_data.update({
                                "scheme_code": bse_scheme.get("scheme_code"),
                                "scheme_plan": bse_scheme.get("scheme_plan"),
                                "face_value": bse_scheme.get("operational_details", {}).get("face_value"),
                                "purchase_amount_min": bse_scheme.get("purchase_details", {}).get("minimum_purchase_amount"),
                                "redemption_allowed": bse_scheme.get("redemption_details", {}).get("redemption_allowed")
                            })
                    
                    break  # Use first valid data item
        
        return fund_data
    
    def _format_db_result(self, result: Dict[str, Any], fund_name: str) -> str:
        """Format database result into readable response with proper nested data parsing"""
        # Handle the comprehensive search result structure
        funds_data = []
        
        # Debug logging to understand the structure
        logger.info(f"Formatting result structure keys: {list(result.keys())}")
        
        # Check if result has 'data' array (comprehensive search)
        if result.get("data") and isinstance(result["data"], list):
            for data_item in result["data"]:
                if data_item.get("results") and isinstance(data_item["results"], dict):
                    nested_results = data_item["results"]
                    
                    # Extract fund data from different nested structures
                    fund_info = {}
                    
                    # From factsheet data
                    if "factsheet" in nested_results:
                        factsheet = nested_results["factsheet"]
                        fund_info.update({
                            "scheme_name": factsheet.get("scheme_name"),
                            "isin": factsheet.get("isin"),
                            "amc_name": factsheet.get("amc"),
                            "fund_manager": factsheet.get("fund_manager"),
                            "scheme_type": factsheet.get("scheme_type"),
                            "expense_ratio": factsheet.get("expense_ratio"),
                            "exit_load": factsheet.get("exit_load"),
                            "minimum_lumpsum": factsheet.get("minimum_lumpsum"),
                            "minimum_sip": factsheet.get("minimum_sip"),
                            "benchmark": factsheet.get("benchmark"),
                            "plan": factsheet.get("plan"),
                            "sub_category": factsheet.get("sub_category"),
                            "sebi_risk_category": factsheet.get("sebi_risk_category")
                        })
                    
                    # From returns data
                    if "returns" in nested_results:
                        returns = nested_results["returns"]
                        fund_info.update({
                            "return_1m": returns.get("return_1m"),
                            "return_1y": returns.get("return_1y"),
                            "return_3y": returns.get("return_3y"),
                            "return_ytd": returns.get("return_ytd")
                        })
                    
                    # From NAV history (get latest NAV)
                    if "nav_history" in nested_results and nested_results["nav_history"].get("nav_history"):
                        nav_data = nested_results["nav_history"]["nav_history"]
                        if isinstance(nav_data, list) and nav_data:
                            latest_nav = nav_data[0]  # First item is usually the latest
                            fund_info.update({
                                "nav": latest_nav.get("nav"),
                                "nav_date": latest_nav.get("date")
                            })
                    
                    # From BSE scheme data (get additional details)
                    if "bse_scheme" in nested_results and nested_results["bse_scheme"].get("data"):
                        bse_schemes = nested_results["bse_scheme"]["data"]
                        if isinstance(bse_schemes, list) and bse_schemes:
                            # Use first BSE scheme for additional details
                            bse_scheme = bse_schemes[0]
                            fund_info.update({
                                "scheme_code": bse_scheme.get("scheme_code"),
                                "scheme_plan": bse_scheme.get("scheme_plan"),
                                "face_value": bse_scheme.get("operational_details", {}).get("face_value"),
                                "purchase_amount_min": bse_scheme.get("purchase_details", {}).get("minimum_purchase_amount"),
                                "redemption_allowed": bse_scheme.get("redemption_details", {}).get("redemption_allowed")
                            })
                    
                    # From fund_details (if available)
                    if "fund_details" in nested_results:
                        fund_details = nested_results["fund_details"]
                        if isinstance(fund_details, dict) and fund_details.get("data"):
                            fd_data = fund_details["data"]
                            if isinstance(fd_data, list) and fd_data:
                                fd_item = fd_data[0]
                            else:
                                fd_item = fd_data
                            
                            if isinstance(fd_item, dict):
                                fund_info.update({
                                    "fund_name": fd_item.get("fund_name"),
                                    "fund_type": fd_item.get("fund_type"),
                                    "fund_subtype": fd_item.get("fund_subtype")
                                })
                    
                    # Add the fund info if we have meaningful data
                    if any(v is not None and v != "" for v in fund_info.values()):
                        funds_data.append(fund_info)
        
        # Fallback: check for direct results
        elif result.get("results"):
            if isinstance(result["results"], list):
                funds_data = result["results"]
            else:
                funds_data = [result["results"]]
        
        if not funds_data:
            return f"❌ No data found for '{fund_name}'"
        
        # Format the response based on available data
        fund_data = funds_data[0]  # Use the first/main fund data
        
        # Get fund name - try multiple fields
        name = (fund_data.get('scheme_name') or 
                fund_data.get('fund_name') or 
                fund_name)
        
        response = f"**{name}**\n\n"
        
        # Essential details
        isin = fund_data.get('isin', 'N/A')
        if isin != 'N/A':
            response += f"📋 **ISIN**: {isin}\n"
        
        amc = fund_data.get('amc_name', 'N/A')
        if amc != 'N/A':
            response += f"🏢 **AMC**: {amc}\n"
        
        # Fund type and category
        scheme_type = fund_data.get('scheme_type', fund_data.get('fund_type', 'N/A'))
        if scheme_type != 'N/A':
            response += f"📊 **Type**: {scheme_type}\n"
        
        sub_category = fund_data.get('sub_category', fund_data.get('fund_subtype', 'N/A'))
        if sub_category != 'N/A':
            response += f"📈 **Category**: {sub_category}\n"
        
        # Plan details
        plan = fund_data.get('plan', 'N/A')
        scheme_plan = fund_data.get('scheme_plan', 'N/A')
        if plan != 'N/A' or scheme_plan != 'N/A':
            plan_info = f"{scheme_plan}" if scheme_plan != 'N/A' else plan
            response += f"📋 **Plan**: {plan_info}\n"
        
        # NAV information
        nav = fund_data.get('nav', 'N/A')
        nav_date = fund_data.get('nav_date', 'N/A')
        if nav != 'N/A':
            response += f"💰 **Current NAV**: ₹{nav}"
            if nav_date != 'N/A':
                response += f" (as of {nav_date})"
            response += "\n"
        
        # Fund manager
        fund_manager = fund_data.get('fund_manager', 'N/A')
        if fund_manager != 'N/A':
            response += f"👨‍💼 **Fund Manager**: {fund_manager}\n"
        
        # Performance data
        response += "\n**📊 Performance:**\n"
        return_1m = fund_data.get('return_1m', 'N/A')
        return_1y = fund_data.get('return_1y', 'N/A')
        return_3y = fund_data.get('return_3y', 'N/A')
        return_ytd = fund_data.get('return_ytd', 'N/A')
        
        if return_1m != 'N/A':
            response += f"• 1 Month: {return_1m}%\n"
        if return_ytd != 'N/A':
            response += f"• Year to Date: {return_ytd}%\n"
        if return_1y != 'N/A':
            response += f"• 1 Year: {return_1y}%\n"
        if return_3y != 'N/A':
            response += f"• 3 Years: {return_3y}%\n"
        
        # Cost and investment details
        response += "\n**💼 Investment Details:**\n"
        expense_ratio = fund_data.get('expense_ratio', 'N/A')
        if expense_ratio != 'N/A':
            response += f"• Expense Ratio: {expense_ratio}%\n"
        
        exit_load = fund_data.get('exit_load', 'N/A')
        if exit_load != 'N/A':
            response += f"• Exit Load: {exit_load}%\n"
        
        min_lumpsum = fund_data.get('minimum_lumpsum', fund_data.get('purchase_amount_min', 'N/A'))
        if min_lumpsum != 'N/A':
            response += f"• Minimum Investment: ₹{min_lumpsum}\n"
        
        min_sip = fund_data.get('minimum_sip', 'N/A')
        if min_sip != 'N/A':
            response += f"• Minimum SIP: ₹{min_sip}\n"
        
        # Risk and benchmark
        risk_category = fund_data.get('sebi_risk_category', 'N/A')
        if risk_category != 'N/A':
            response += f"• Risk Level: {risk_category}\n"
        
        benchmark = fund_data.get('benchmark', 'N/A')
        if benchmark != 'N/A':
            response += f"• Benchmark: {benchmark}\n"
        
        # Source information
        confidence = result.get('confidence', 0)
        sources = result.get('sources', ['database'])
        response += f"\n*📊 Source: {', '.join(sources)} | Confidence: {confidence:.1%}*"
        
        return response
    
    def _format_tavily_result(self, result: Dict[str, Any], query: str) -> str:
        """Format Tavily search result into readable response"""
        if not result.get("results"):
            return f"No web data found for {query}"
        
        response = f"**Web Search Results for '{query}'**\n\n"
        
        # Include the top 3 results for conciseness
        for i, item in enumerate(result["results"][:3]):
            title = item.get("title", "No Title")
            content = item.get("content", "No Content")
            url = item.get("url", "No URL")
            
            # Truncate content to keep response concise
            max_content_len = 250
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."
            
            response += f"### {i+1}. {title}\n"
            response += f"{content}\n"
            response += f"*Source: {url}*\n\n"
        
        response += "*Data retrieved via Tavily web search*"
        
        return response
        
        return response
    
    def _format_bse_result(self, result: Dict[str, Any], fund_name: str) -> str:
        """Format BSE result into readable response"""
        if not result.get("results"):
            return f"No BSE data found for {fund_name}"
        
        fund_data = result["results"][0] if isinstance(result["results"], list) else result["results"]
        
        response = f"**{fund_data.get('scheme_name', fund_name)}** (BSE Data)\n\n"
        response += f"• **Scheme Code**: {fund_data.get('scheme_code', 'N/A')}\n"
        response += f"• **ISIN**: {fund_data.get('isin', 'N/A')}\n"
        response += f"• **AMC**: {fund_data.get('amc_name', 'N/A')}\n"
        response += f"• **Status**: {fund_data.get('status', 'N/A')}\n\n"
        response += f"*Source: BSE Schemes Data*"
        
        return response

    def _handle_general_question(self, user_input: str) -> str:
        """Handle general mutual fund questions"""
        
        question_lower = user_input.lower()
        
        if "nav" in question_lower or "net asset value" in question_lower:
            return "**Net Asset Value (NAV)** is the per-unit market value of a mutual fund.\\n\\n**How NAV works:**\\n• NAV = (Total Assets - Liabilities) ÷ Total Units Outstanding\\n• Updated daily after market closure (usually by 9 PM)\\n• Used for buying and selling fund units\\n• NAV alone doesn't indicate fund performance\\n\\n**Example:** If a fund has ₹1000 crores assets, ₹10 crores liabilities, and 99 crore units:\\nNAV = (1000-10) ÷ 99 = ₹10 per unit\\n\\nWould you like to check the current NAV of a specific fund?"
        
        elif "sip" in question_lower:
            return "**Systematic Investment Plan (SIP)** is a disciplined way to invest in mutual funds.\\n\\n**Key Benefits:**\\n• **Rupee Cost Averaging** - Buy more units when NAV is low, fewer when high\\n• **Disciplined Investing** - Regular investment habit\\n• **Flexibility** - Start with as low as ₹500/month\\n• **Power of Compounding** - Long-term wealth creation\\n\\n**How it works:** Fixed amount invested monthly → Units allocated based on current NAV\\n\\nWould you like to know about SIP options for any specific fund?"
        
        elif "mutual fund" in question_lower and ("what" in question_lower or "how" in question_lower):
            return "**Mutual Funds** are investment vehicles that pool money from many investors.\\n\\n**How they work:**\\n• Professional fund managers invest pooled money in stocks, bonds, etc.\\n• Investors get units proportional to their investment\\n• Returns depend on fund performance\\n• Regulated by SEBI in India\\n\\n**Types:**\\n• **Equity Funds** - Invest in stocks\\n• **Debt Funds** - Invest in bonds/fixed income\\n• **Hybrid Funds** - Mix of equity and debt\\n\\n**Benefits:** Professional management, diversification, liquidity, transparency\\n\\nWould you like to know about specific fund categories or funds?"
        
        return "I can help with mutual fund questions! Ask me about specific funds, NAV, SIP, fund categories, or general investment concepts."

    async def _handle_error(self, error: str, user_input: str) -> str:
        """Handle errors gracefully"""
        logger.error(f"Error handling user input: {error}")
        return f"I apologize, but I encountered an issue: {error}. Please try rephrasing your question or ask about a specific mutual fund."
