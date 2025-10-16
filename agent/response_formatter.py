"""
Response formatter for the Mutual Funds Agent
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .config import AgentConfig
from .intent_parser import Intent, SentimentLabel
from utils.logger import get_logger

logger = get_logger(__name__)

class ResponseFormatter:
    """Formats agent responses according to the specified format"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
    
    async def format_response(self, result: Dict[str, Any], intent: Intent,
                            user_name: Optional[str] = None,
                            sources_used: List[Dict[str, Any]] = None,
                            confidence: float = 0.0) -> str:
        """Format the final response according to specifications"""
        
        if sources_used is None:
            sources_used = []
        
        # Comprehensive error checking
        try:
            logger.debug(f"format_response called with result type: {type(result)}")
            logger.debug(f"Intent type: {type(intent)}")
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                logger.error(f"Result is not a dict: {type(result)}, value: {str(result)[:200]}")
                return "I encountered an error processing your request. Please try again with a more specific fund name."
            
            # Handle clarification responses
            if result.get("type") == "clarification":
                return self._format_clarification_response(result, intent, user_name)
            
            # Handle error responses
            if result.get("type") == "error" or not result.get("found", False):
                return self._format_error_response(result, intent, user_name)
            
            # Handle successful responses
            return await self._format_success_response(result, intent, user_name, sources_used, confidence)
            
        except Exception as e:
            logger.error(f"Error in format_response: {str(e)}")
            logger.error(f"Result type: {type(result)}, Intent type: {type(intent)}")
            if isinstance(result, dict):
                logger.error(f"Result keys: {result.keys()}")
            return f"I encountered an error: {str(e)}. Please try again."
    
    def _format_clarification_response(self, result: Dict[str, Any], 
                                     intent: Intent, user_name: Optional[str]) -> str:
        """Format clarification request"""
        
        greeting = self._get_dynamic_greeting(intent.sentiment if hasattr(intent, 'sentiment') and intent.sentiment else None, user_name)
        
        return f"""{greeting}

🤔 **I need a bit more information to help you better.**

{result['question']}

**Quick options:**
1. Provide the exact fund name
2. Ask a general question about mutual funds
3. Browse fund categories

What would you prefer?

---
```json
{{
    "method_used": "LangChain zero-shot",
    "tools_used": ["INTENT_PARSER"],
    "retrieval_path": ["CLARIFICATION_REQUIRED"],
    "sources": [],
    "confidence_score": {result.get('confidence', 0.0)},
    "was_confirmation_required": true
}}
```"""
    
    def _format_error_response(self, result: Dict[str, Any], 
                             intent: Intent, user_name: Optional[str]) -> str:
        """Format error response"""
        
        greeting = self._get_dynamic_greeting(intent.sentiment if hasattr(intent, 'sentiment') and intent.sentiment else None, user_name)
        error_msg = result.get("error", "Unknown error occurred")
        
        return f"""{greeting}

**❌ I couldn't find the information you're looking for**

**Issue:** {error_msg}

**What you can try:**
1. 🔄 **Retry** with exact fund name (e.g., "Axis Bluechip Fund")
2. 🔍 **Search** by AMC name (e.g., "HDFC funds")
3. 📞 **Contact support** if this continues

**Alternative:** I can help with general mutual fund questions while we resolve this.

What would you like to do next?

**Confidence:** Low (0.1/1.0) - Unable to retrieve data

**Compliance:** Not financial advice; confirm with official sources or your advisor.

---
```json
{{
    "method_used": "LangChain zero-shot", 
    "tools_used": ["DB_API"],
    "retrieval_path": ["DB_ERROR"],
    "sources": [],
    "confidence_score": 0.1,
    "was_confirmation_required": false
}}
```"""
    
    async def _format_success_response(self, result: Dict[str, Any], intent: Intent,
                                     user_name: Optional[str], sources_used: List[Dict[str, Any]],
                                     confidence: float) -> str:
        """Format successful response with complete structure"""
        
        # Safe sentiment extraction with comprehensive error handling
        safe_sentiment = None
        if hasattr(intent, 'sentiment'):
            if intent.sentiment and hasattr(intent.sentiment, 'label'):
                safe_sentiment = intent.sentiment
            else:
                logger.debug(f"Sentiment object invalid: {type(intent.sentiment)}")
        
        greeting = self._get_dynamic_greeting(safe_sentiment, user_name)
        
        # Extract main fund data with safety checks
        fund_data = result.get("results", [])
        if not fund_data:
            logger.warning("No fund data found in results")
            return await self._format_error_response(result, intent, user_name)
        
        # Handle different data structures safely
        main_fund = None
        if isinstance(fund_data, list):
            if len(fund_data) > 0:
                main_fund = fund_data[0]
            else:
                logger.warning("Fund data list is empty")
                return await self._format_error_response(result, intent, user_name)
        elif isinstance(fund_data, dict):
            main_fund = fund_data
        else:
            logger.warning(f"Fund data has unexpected type: {type(fund_data)}")
            return await self._format_error_response(result, intent, user_name)
        
        # Ensure main_fund is a dictionary
        if not isinstance(main_fund, dict):
            logger.error(f"main_fund is not a dict, type: {type(main_fund)}, value: {str(main_fund)[:100]}")
            return await self._format_error_response({
                "type": "error", 
                "found": False, 
                "error": f"Invalid fund data format: expected dict, got {type(main_fund)}"
            }, intent, user_name)
        
        # 1. Dynamic greeting
        response_parts = [greeting]
        
        # 2. TL;DR
        tl_dr = self._generate_tldr(main_fund, intent)
        response_parts.append(f"**📋 TL;DR:** {tl_dr}")
        
        # 3. Key Answer
        key_points = self._generate_key_points(main_fund, result)
        response_parts.append("**🔑 Key Details:**")
        for point in key_points:
            response_parts.append(f"• {point}")
        
        # 4. Detailed Explanation
        detailed_explanation = self._generate_detailed_explanation(main_fund, result, intent)
        response_parts.append("**📊 Detailed Information:**")
        response_parts.append(detailed_explanation)
        
        # 5. Evidence & Sources
        evidence_section = self._generate_evidence_section(result, sources_used)
        response_parts.append("**📚 Evidence & Sources:**")
        response_parts.append(evidence_section)
        
        # 6. Actions / Next Steps
        next_steps = self._generate_next_steps(main_fund, intent)
        response_parts.append("**🎯 Suggested Next Steps:**")
        response_parts.append(next_steps)
        
        # 7. Follow-up prompt
        follow_up = self._generate_follow_up_prompt(intent, main_fund)
        response_parts.append(follow_up)
        
        # 8. Rationale
        rationale = self._generate_rationale(result)
        response_parts.append(f"**🧠 Source Selection:** {rationale}")
        
        # 9. Confidence
        confidence_section = self._generate_confidence_section(confidence, result)
        response_parts.append(f"**📈 Confidence:** {confidence_section}")
        
        # 10. Compliance disclaimer
        response_parts.append("**⚖️ Disclaimer:** Not financial advice; confirm with official sources or your advisor.")
        
        # 11. Metadata JSON
        metadata = self._generate_metadata(result, sources_used, confidence, intent)
        response_parts.append("---")
        response_parts.append("```json")
        response_parts.append(json.dumps(metadata, indent=2))
        response_parts.append("```")
        
        return "\n\n".join(response_parts)
    
    def _get_dynamic_greeting(self, sentiment, user_name: Optional[str]) -> str:
        """Generate dynamic greeting based on sentiment"""
        
        name_part = f" {user_name}" if user_name else ""
        
        # Check if sentiment is an object with a label attribute
        if sentiment and hasattr(sentiment, 'label'):
            if sentiment.label == SentimentLabel.POSITIVE:
                return f"😊 Hello{name_part}! Great to see your interest in mutual funds!"
            elif sentiment.label == SentimentLabel.NEGATIVE:
                return f"👋 Hi{name_part}, I understand you might have concerns. Let me help you with that."
            elif sentiment.label == SentimentLabel.ANGRY:
                return f"🤝 Hi{name_part}, I can see you're frustrated. Let me do my best to resolve this quickly."
            elif sentiment.label == SentimentLabel.URGENT:
                return f"⚡ Hi{name_part}! I'll get you the information you need right away."
        
        # Default greeting if sentiment is not a proper object or doesn't match
        return f"👋 Hello{name_part}! I'm here to help with your mutual fund questions."
    
    def _generate_tldr(self, fund_data: Dict[str, Any], intent: Intent) -> str:
        """Generate one-sentence summary"""
        
        # Ensure fund_data is a dictionary
        if not isinstance(fund_data, dict):
            return f"Fund information found but format is not readable"
        
        fund_name = (fund_data.get("scheme_name") or 
                    fund_data.get("fund_name") or 
                    "Unknown Fund")
        nav = fund_data.get("nav", "N/A")
        amc = fund_data.get("amc_name", "N/A")
        category = fund_data.get("fund_type") or fund_data.get("scheme_type", "")
        
        if intent.intent.value == "nav_request":
            return f"{fund_name} current NAV is ₹{nav}"
        elif intent.intent.value == "fund_details":
            return f"{fund_name} is a {category} fund by {amc} with NAV ₹{nav}"
        else:
            return f"{fund_name} ({amc}) - {category if category else 'Mutual Fund'}"
    
    def _generate_key_points(self, fund_data: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Generate 2-4 key bullet points"""
        
        # Ensure fund_data is a dictionary
        if not isinstance(fund_data, dict):
            return ["Fund data format is not readable"]
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {}
        
        points = []
        source_info = f"(Source: {result.get('source', 'Unknown')} — {result.get('retrieved_at', 'Unknown date')[:10]})"
        
        if fund_data.get("nav"):
            points.append(f"**Current NAV:** ₹{fund_data['nav']} as of {fund_data.get('nav_date', 'N/A')} {source_info}")
        
        if fund_data.get("fund_manager"):
            points.append(f"**Fund Manager:** {fund_data['fund_manager']}")
        
        if fund_data.get("aum"):
            points.append(f"**Assets Under Management:** {fund_data['aum']}")
        
        if fund_data.get("category"):
            points.append(f"**Category:** {fund_data['category']}")
        
        return points[:4]  # Maximum 4 points
    
    def _generate_detailed_explanation(self, fund_data: Dict[str, Any], 
                                     result: Dict[str, Any], intent: Intent) -> str:
        """Generate detailed explanation with subsections"""
        
        # Ensure fund_data is a dictionary
        if not isinstance(fund_data, dict):
            return "Fund data is not in a readable format."
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {}
        
        sections = []
        
        # Fund Overview
        if fund_data.get("fund_name") or fund_data.get("scheme_name"):
            fund_name = fund_data.get("fund_name") or fund_data.get("scheme_name")
            sections.append(f"**Fund Overview:** {fund_name} is managed by {fund_data.get('fund_manager', 'N/A')} and falls under the {fund_data.get('category', fund_data.get('scheme_type', 'N/A'))} category.")
        
        # Current Valuation
        if fund_data.get("nav"):
            nav_date = fund_data.get("nav_date", "N/A")
            sections.append(f"**Current Valuation:** The fund's NAV stands at ₹{fund_data['nav']} as of {nav_date}. This represents the per-unit value of the fund after accounting for all assets and liabilities.")
        
        # Fund Size
        if fund_data.get("aum"):
            sections.append(f"**Fund Size:** With ₹{fund_data['aum']} in assets under management, this indicates the total value of investments managed by the fund.")
        
        # Data Source
        source = result.get("source", "Unknown")
        retrieved_at = result.get("retrieved_at", "Unknown")[:19] if result.get("retrieved_at") else "Unknown"
        sections.append(f"**Data Freshness:** Information sourced from {source} at {retrieved_at}.")
        
        return "\n\n".join(sections) if sections else "No detailed information available."
    
    def _generate_evidence_section(self, result: Dict[str, Any], 
                                 sources_used: List[Dict[str, Any]]) -> str:
        """Generate evidence and sources section"""
        
        evidence_items = []
        
        # Primary source
        source_type = result.get("source", "Unknown")
        confidence = result.get("confidence", 0.0)
        retrieved_at = result.get("retrieved_at", "Unknown")[:10]
        
        evidence_items.append(
            f"1. **{source_type}** - Retrieved: {retrieved_at} - "
            f"Confidence: {confidence:.2f} - Primary fund data source"
        )
        
        # Additional sources
        for i, source in enumerate(sources_used, 2):
            evidence_items.append(
                f"{i}. **{source.get('type', 'Unknown')}** - "
                f"URL: {source.get('url', 'N/A')} - "
                f"Retrieved: {source.get('retrieved_at', 'N/A')[:10]}"
            )
        
        return "\n".join(evidence_items)
    
    def _generate_next_steps(self, fund_data: Dict[str, Any], intent: Intent) -> str:
        """Generate suggested next steps"""
        
        steps = []
        fund_name = fund_data.get("fund_name", "this fund")
        
        if intent.intent.value == "nav_request":
            steps.extend([
                f"📈 **Get performance data** for {fund_name}",
                f"🔍 **Compare** with similar funds in the same category",
                f"📊 **View holdings** to understand portfolio composition"
            ])
        elif intent.intent.value == "fund_query":
            steps.extend([
                f"📊 **Check historical performance** of {fund_name}",
                f"💰 **View detailed fund factsheet** with all metrics",
                f"🏆 **Compare** with benchmark and peer funds"
            ])
        else:
            steps.extend([
                f"📈 **Explore performance trends** for {fund_name}",
                f"🔍 **Get detailed fund analysis** including holdings",
                f"💡 **Ask specific questions** about this fund"
            ])
        
        return "\n".join(steps)
    
    def _generate_follow_up_prompt(self, intent: Intent, fund_data: Dict[str, Any]) -> str:
        """Generate dynamic follow-up prompt with related questions"""
        
        fund_name = (fund_data.get("scheme_name") or 
                    fund_data.get("fund_name") or 
                    "this fund")
        amc = fund_data.get("amc_name", "")
        category = fund_data.get("fund_type") or fund_data.get("scheme_type", "")
        
        # Generate contextual related questions
        related_questions = []
        
        if intent.intent.value == "nav_request":
            related_questions = [
                f"📈 What are the historical returns of {fund_name}?",
                f"💰 What is the expense ratio of {fund_name}?",
                f"🔍 Compare {fund_name} with similar funds",
                f"📊 Show me the fund manager details for {fund_name}"
            ]
        elif intent.intent.value == "fund_details":
            related_questions = [
                f"📈 How has {fund_name} performed over the years?",
                f"💡 What are the top holdings of {fund_name}?",
                f"⚖️ Is {fund_name} suitable for long-term investment?",
                f"🆚 Compare {fund_name} with other {category} funds"
            ]
        elif intent.intent.value == "compare_funds":
            related_questions = [
                f"💰 Which has better returns - {fund_name} or its competitors?",
                f"📊 Show me detailed comparison metrics",
                f"🎯 Which fund is better for SIP investment?",
                f"🔍 Analyze risk-adjusted returns for these funds"
            ]
        else:
            # General related questions based on available data
            if amc:
                related_questions.append(f"🏢 Show me other top funds from {amc}")
            if category:
                related_questions.append(f"📊 What are the best {category} funds?")
            related_questions.extend([
                f"💡 Explain the investment strategy of {fund_name}",
                f"⚡ Is now a good time to invest in {fund_name}?",
                f"🎯 What is the minimum SIP amount for {fund_name}?"
            ])
        
        # Format the follow-up section
        questions_text = "\n".join([f"• {q}" for q in related_questions[:4]])  # Limit to 4 questions
        
        return f"""**🤔 Want to know more? Try asking:**

{questions_text}

**Or explore:**
• General mutual fund advice and strategies
• Market trends and investment opportunities  
• Portfolio building and asset allocation tips

*Just ask naturally - I understand conversational queries!*"""
    
    def _generate_rationale(self, result: Dict[str, Any]) -> str:
        """Generate rationale for source selection"""
        
        source = result.get("source", "Unknown")
        
        if source == "internal_db":
            return "Used internal database for reliable, structured fund data."
        elif source == "AMFI_NAV_FILE":
            return "Retrieved from official AMFI NAV file for authoritative pricing data."
        elif source == "BSE_SCHEMES_API":
            return "Accessed BSE schemes database for comprehensive fund details."
        else:
            return "Selected best available source based on data quality and recency."
    
    def _generate_confidence_section(self, confidence: float, result: Dict[str, Any]) -> str:
        """Generate confidence section with explanation"""
        
        if confidence >= 0.8:
            level = "High"
            explanation = "based on official API data"
        elif confidence >= 0.6:
            level = "Medium" 
            explanation = "based on reliable web sources"
        else:
            level = "Low"
            explanation = "due to limited or conflicting data"
        
        return f"{level} ({confidence:.2f}/1.0) {explanation}"
    
    def _generate_metadata(self, result: Dict[str, Any], sources_used: List[Dict[str, Any]],
                          confidence: float, intent: Intent) -> Dict[str, Any]:
        """Generate metadata JSON"""
        
        tools_used = ["INTENT_PARSER"]
        retrieval_path = []
        
        # Add tools based on result source
        source = result.get("source", "")
        if "db" in source.lower() or "api" in source.lower():
            tools_used.append("DB_API")
            retrieval_path.append("DB")
        
        if "amfi" in source.lower():
            tools_used.append("AMFI_WEBSCRAPE")
            retrieval_path.append("AMFI")
        
        if "moonshot" in source.lower() or "llm" in source.lower():
            tools_used.append("MOONSHOT_LLM")
            retrieval_path.append("LLM")
        
        # Format sources for metadata
        formatted_sources = []
        for source in sources_used:
            formatted_sources.append({
                "type": source.get("type", "Unknown"),
                "id_or_title": source.get("id", source.get("title", "N/A")),
                "url": source.get("url", ""),
                "retrieved_at": source.get("retrieved_at", "")[:10],
                "confidence": source.get("confidence", confidence)
            })
        
        return {
            "method_used": "LangChain zero-shot",
            "tools_used": tools_used,
            "retrieval_path": retrieval_path,
            "sources": formatted_sources,
            "confidence_score": confidence,
            "was_confirmation_required": intent.clarity == "low"
        }
