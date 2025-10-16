"""
Tool orchestrator for calling different APIs and services
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlencode

from .config import AgentConfig
from .intent_parser import IntentType
from utils.logger import get_logger

logger = get_logger(__name__)

class ToolOrchestrator:
    """Orchestrates calls to different tools (DB API, AMFI, Web Scraper, Moonshot AI)"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
    
    async def call_db_api(self, fund_name: Optional[str] = None, 
                         metric: Optional[str] = None, 
                         deep_search: bool = True) -> Dict[str, Any]:
        """
        Deep, comprehensive database search - thorough analysis across all endpoints
        
        Args:
            fund_name: Name of the fund to search for
            metric: Specific metric to retrieve  
            deep_search: If True, performs exhaustive search across all APIs
        """
        
        if not fund_name:
            return {"found": False, "error": "No fund name provided", "confidence": 0.0}
        
        logger.info(f"Starting DEEP DB search for: '{fund_name}' with metric: {metric}")
        
        # Phase 1: Direct exact match search across all APIs
        logger.info("Phase 1: Exact match search across all endpoints")
        exact_results = await self._deep_exact_search(fund_name, metric)
        
        if exact_results.get("found") and exact_results.get("results"):
            logger.info(f"Phase 1 SUCCESS: Found {len(exact_results.get('results', []))} exact matches")
            return exact_results
            
        # Phase 2: Intelligent keyword extraction and search
        logger.info("Phase 2: Intelligent keyword extraction and multi-strategy search")
        keyword_results = await self._intelligent_keyword_search(fund_name, metric)
        
        if keyword_results.get("found") and keyword_results.get("results"):
            logger.info(f"Phase 2 SUCCESS: Found {len(keyword_results.get('results', []))} keyword matches")
            return keyword_results
            
        # Phase 3: Fuzzy matching and partial searches
        logger.info("Phase 3: Fuzzy matching and partial search strategies")
        fuzzy_results = await self._fuzzy_match_search(fund_name, metric)
        
        if fuzzy_results.get("found") and fuzzy_results.get("results"):
            logger.info(f"Phase 3 SUCCESS: Found {len(fuzzy_results.get('results', []))} fuzzy matches")
            return fuzzy_results
            
        # Phase 4: AMC-level search (search by fund house)
        logger.info("Phase 4: AMC-level and category-based search")
        amc_results = await self._amc_level_search(fund_name, metric)
        
        if amc_results.get("found") and amc_results.get("results"):
            logger.info(f"Phase 4 SUCCESS: Found {len(amc_results.get('results', []))} AMC matches")
            return amc_results
            
        logger.warning(f"All 4 phases completed - no results found for: {fund_name}")
        return {"found": False, "error": f"No funds found after exhaustive search for '{fund_name}'", "confidence": 0.0}
    
    def _normalize_fund_data(self, fund: dict, source: str) -> dict:
        """Normalize fund data from different API sources"""
        normalized = {}
        
        # Extract scheme/fund name
        normalized['scheme_name'] = (
            fund.get('scheme_name') or 
            fund.get('fund_name') or 
            fund.get('name') or 
            fund.get('scheme')
        )
        
        # Extract AMC/Fund House name
        normalized['amc_name'] = (
            fund.get('amc_name') or
            fund.get('amc_code') or  # BSE uses amc_code
            fund.get('fund_house') or
            fund.get('fund_company') or
            fund.get('management_company')
        )
        
        # Extract fund type/category  
        normalized['fund_type'] = (
            fund.get('fund_type') or
            fund.get('scheme_type') or
            fund.get('category') or
            fund.get('fund_category')
        )
        
        # Extract NAV
        normalized['nav'] = (
            fund.get('nav') or
            fund.get('current_nav') or
            fund.get('net_asset_value')
        )
        
        # Extract ISIN - CRITICAL for identification
        normalized['isin'] = fund.get('isin')
        
        # Extract plan information
        normalized['plan'] = (
            fund.get('plan') or
            fund.get('scheme_plan') or
            fund.get('option')
        )
        
        # Extract performance data
        normalized['return_1y'] = fund.get('return_1y')
        normalized['return_3y'] = fund.get('return_3y')
        normalized['return_5y'] = fund.get('return_5y')
        
        # Extract cost information
        normalized['expense_ratio'] = fund.get('expense_ratio')
        
        # Extract risk information
        normalized['sebi_risk_category'] = (
            fund.get('sebi_risk_category') or
            fund.get('risk_level') or
            fund.get('risk_category')
        )
        
        # Extract fund manager
        normalized['fund_manager'] = fund.get('fund_manager')
        
        # BSE-specific fields
        if source == 'bse_schemes_api':
            normalized['minimum_purchase_amount'] = fund.get('minimum_purchase_amount')
            normalized['minimum_additional_amount'] = fund.get('minimum_additional_amount')
            normalized['sip_flag'] = fund.get('sip_flag')
            normalized['sip_minimum_amount'] = fund.get('sip_minimum_amount')
            normalized['redemption_allowed'] = fund.get('redemption_allowed')
            normalized['purchase_allowed'] = fund.get('purchase_allowed')
            normalized['benchmark'] = fund.get('benchmark')
            normalized['launch_date'] = fund.get('launch_date')
            normalized['aum'] = fund.get('aum')
            
        # Preserve any additional fields from the original fund data that might be useful
        for key in ['fund_subtype', 'scheme_code', 'sub_category', 'exit_load', 'minimum_lumpsum', 'minimum_sip']:
            if key in fund:
                normalized[key] = fund[key]
            
        # Ensure no None values, but keep empty strings
        return {k: v for k, v in normalized.items() if v is not None}

    async def _comprehensive_db_search(self, fund_name: str, metric: Optional[str] = None) -> Dict[str, Any]:
        """Comprehensive search with intelligent filtering to return only relevant funds"""
        try:
            # Extract and understand what user is asking for
            extracted_fund_name = self._extract_fund_name_from_query(fund_name)
            logger.info(f"Original query: '{fund_name}' → Extracted: '{extracted_fund_name}'")
            
            # Search all endpoints in parallel
            search_tasks = [
                self._search_funds_api(extracted_fund_name, metric),
                self._search_bse_schemes_api(extracted_fund_name),
                self._search_funds_by_name_pattern(extracted_fund_name)
            ]
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Aggregate and normalize results
            all_results = []
            sources_used = []
            highest_confidence = 0.0
            
            for i, result in enumerate(results):
                if isinstance(result, dict) and result.get("found", False):
                    source = result.get("source", f"endpoint_{i}")
                    if "results" in result:
                        raw_results = result["results"]
                        if isinstance(raw_results, list):
                            for fund in raw_results:
                                if isinstance(fund, dict):
                                    normalized_fund = self._normalize_fund_data(fund, source)
                                    if normalized_fund.get('scheme_name'):
                                        all_results.append(normalized_fund)
                        else:
                            if isinstance(raw_results, dict):
                                normalized_fund = self._normalize_fund_data(raw_results, source)
                                if normalized_fund.get('scheme_name'):
                                    all_results.append(normalized_fund)
                    sources_used.append(source)
                    highest_confidence = max(highest_confidence, result.get("confidence", 0.0))
            
            if all_results:
                # Filter results to match user's specific request
                filtered_results = self._filter_results_for_user_query(all_results, fund_name, extracted_fund_name)
                
                # Remove duplicates
                unique_results = self._remove_duplicate_funds(filtered_results)
                
                return {
                    "found": True,
                    "results": unique_results,
                    "confidence": highest_confidence,
                    "sources": sources_used,
                    "total_results": len(unique_results),
                    "search_type": "comprehensive_db_search",
                    "retrieved_at": datetime.now().isoformat()
                }
            else:
                return {
                    "found": False,
                    "error": f"No funds found for '{fund_name}'",
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error in comprehensive DB search: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}

    def _filter_results_for_user_query(self, results: List[dict], original_query: str, extracted_name: str) -> List[dict]:
        """Filter results to only include funds that match what user actually asked for"""
        if not results:
            return []
        
        query_lower = original_query.lower()
        extracted_lower = extracted_name.lower()
        
        # For general questions like "what is mutual funds", return empty - use Tavily instead
        general_terms = ['what is', 'explain', 'how to', 'why', 'when', 'where', 'tell me about mutual funds in general']
        if any(term in query_lower for term in general_terms) and 'mutual funds' in query_lower and not any(amc in query_lower for amc in ['dsp', 'axis', 'hdfc', 'sbi', 'icici']):
            logger.info("Detected general question - should use Tavily, returning empty DB results")
            return []
        
        # Identify specific fund houses mentioned
        amc_keywords = {
            'dsp': ['dsp'],
            'axis': ['axis'],
            'hdfc': ['hdfc'],
            'icici': ['icici'],
            'sbi': ['sbi'],
            'aditya birla': ['birla', 'aditya'],
            'edelweiss': ['edelweiss'],
            'baroda': ['baroda', 'bnp'],
            '360 one': ['360', 'one'],
            'kotak': ['kotak'],
            'franklin': ['franklin']
        }
        
        target_amcs = []
        for amc_name, keywords in amc_keywords.items():
            if any(keyword in query_lower or keyword in extracted_lower for keyword in keywords):
                target_amcs.append(amc_name)
        
        # If specific fund houses mentioned, filter by them
        if target_amcs:
            filtered_results = []
            for fund in results:
                fund_amc = fund.get('amc_name', '').lower()
                fund_name = fund.get('scheme_name', '').lower()
                
                # Check if this fund belongs to requested AMCs
                for target_amc in target_amcs:
                    amc_keywords_list = amc_keywords[target_amc]
                    if any(keyword in fund_amc for keyword in amc_keywords_list):
                        filtered_results.append(fund)
                        break
            
            logger.info(f"Filtered from {len(results)} to {len(filtered_results)} results for AMCs: {target_amcs}")
            return filtered_results
        
        # If no specific AMCs mentioned but specific fund name, keep all matching results
        return results[:20]  # Limit to 20 most relevant
    
    async def _search_funds_api(self, fund_name: str, metric: Optional[str] = None) -> Dict[str, Any]:
        """Search the main funds API endpoint"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/"
            params = {}
            if fund_name:
                params["scheme_name"] = fund_name
            if metric:
                params["metric"] = metric
            
            logger.info(f"Searching funds API with URL: {url}, params: {params}")
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        api_response = await response.json()
                        logger.info(f"API returned response type: {type(api_response)}")
                        
                        # Handle the API response structure - it may have 'data' wrapper
                        data = api_response
                        if isinstance(api_response, dict):
                            if 'data' in api_response:
                                data = api_response['data']
                                logger.info(f"Found 'data' wrapper with {len(data) if isinstance(data, list) else 'non-list'} items")
                            else:
                                logger.info(f"API response keys: {list(api_response.keys())}")
                        
                        # Debug: log first result structure
                        if data and len(data) > 0:
                            first_item = data[0] if isinstance(data, list) else data
                            logger.info(f"First data item keys: {list(first_item.keys()) if isinstance(first_item, dict) else 'not dict'}")
                            logger.info(f"First data item scheme_name: {first_item.get('scheme_name', 'N/A') if isinstance(first_item, dict) else 'N/A'}")
                        
                        if data and len(data) > 0:
                            # Filter results to ensure they match the search term
                            filtered_results = []
                            search_terms = fund_name.lower().split()
                            
                            logger.info(f"Filtering {len(data)} results for search terms: {search_terms}")
                            
                            for fund in data:
                                if isinstance(fund, dict):
                                    scheme_name = fund.get('scheme_name', '').lower()
                                    amc_name = fund.get('amc_name', '').lower()
                                    
                                    # More strict matching - for Baroda BNP Paribas, require all key terms
                                    matches = False
                                    
                                    # Special case for Baroda BNP Paribas
                                    if 'baroda' in search_terms and 'bnp' in search_terms:
                                        if 'baroda' in scheme_name and 'bnp' in scheme_name:
                                            matches = True
                                        elif 'baroda' in amc_name and 'bnp' in amc_name:
                                            matches = True
                                    else:
                                        # General matching - search term must be in scheme_name or AMC name
                                        for term in search_terms:
                                            if len(term) >= 3:  # Only check terms with 3+ characters
                                                if term in scheme_name or term in amc_name:
                                                    matches = True
                                                    break
                                    
                                    if matches:
                                        filtered_results.append(fund)
                                        logger.info(f"Matched fund: {fund.get('scheme_name', 'N/A')} from {fund.get('amc_name', 'N/A')}")
                            
                            if filtered_results:
                                logger.info(f"Found {len(filtered_results)} matching funds after filtering")
                                # Safely limit results
                                limited_results = []
                                try:
                                    if isinstance(filtered_results, list):
                                        limited_results = filtered_results[:5]  # Limit to top 5 matches
                                    else:
                                        limited_results = [filtered_results]
                                except (TypeError, AttributeError) as e:
                                    logger.error(f"Error slicing filtered_results: {e}")
                                    limited_results = [filtered_results] if filtered_results else []
                                
                                return {
                                    "found": True,
                                    "results": limited_results,
                                    "source": "funds_api",
                                    "confidence": 0.9,
                                    "search_term": fund_name
                                }
                            else:
                                logger.warning(f"No matching funds found for '{fund_name}' in {len(data)} results")
                                # Check what funds were actually returned - ensure data is a list
                                sample_data = []
                                try:
                                    if isinstance(data, list):
                                        sample_data = data[:3]
                                    elif data:
                                        sample_data = [data]
                                except (TypeError, AttributeError) as e:
                                    logger.error(f"Error creating sample_data: {e}")
                                    sample_data = []
                                
                                sample_funds = []
                                try:
                                    for f in sample_data:
                                        if isinstance(f, dict):
                                            name = f.get('scheme_name', 'N/A')
                                            amc = f.get('amc_name', 'N/A')
                                            sample_funds.append(f"{name} ({amc})")
                                except Exception as e:
                                    logger.error(f"Error processing sample funds: {e}")
                                    sample_funds = ["Error processing sample data"]
                                
                                logger.info(f"Sample of returned funds: {sample_funds}")
                                
                                return {
                                    "found": False,
                                    "error": f"No funds matching '{fund_name}' found in database. API returned funds from other AMCs instead.",
                                    "source": "funds_api",
                                    "confidence": 0.0,
                                    "total_unfiltered_results": len(data) if isinstance(data, list) else 1,
                                    "sample_results": sample_funds
                                }
                        else:
                            return {
                                "found": False,
                                "error": "No data returned from API",
                                "source": "funds_api",
                                "confidence": 0.0
                            }
                    
                    return {"found": False, "error": f"Funds API status {response.status}", "confidence": 0.0}
                        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Funds API error: {error_msg}")
            
            # Handle specific error types
            if "unhashable type" in error_msg:
                logger.error("Slice operation error detected in funds API")
                return {
                    "found": False, 
                    "error": "Internal data processing error", 
                    "confidence": 0.0,
                    "source": "funds_api"
                }
            
            return {"found": False, "error": error_msg, "confidence": 0.0}
    
    async def _search_bse_schemes_api(self, scheme_name: str) -> Dict[str, Any]:
        """Search BSE schemes API"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/bse-schemes/"
            params = {"scheme_name": scheme_name, "active_only": "true"}  # Fix: Use string instead of boolean
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, dict) and "schemes" in data and data["schemes"]:
                            return {
                                "found": True,
                                "results": data["schemes"],
                                "confidence": 0.95,
                                "source": "bse_schemes_api",
                                "pagination": data.get("pagination", {})
                            }
                    
                    return {"found": False, "error": f"BSE API status {response.status}", "confidence": 0.0}
                        
        except Exception as e:
            logger.error(f"BSE schemes API error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    async def _search_funds_by_name_pattern(self, fund_name: str) -> Dict[str, Any]:
        """Search funds API with different name patterns and parameters"""
        try:
            # Try different parameter variations
            search_patterns = [
                {"name": fund_name},
                {"fund_name": fund_name},
                {"search": fund_name},
                {"q": fund_name}
            ]
            
            for params in search_patterns:
                try:
                    url = f"{self.config.PRODUCTION_API_BASE}/api/funds/"
                    headers = {"Accept": "application/json"}
                    
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                        async with session.get(url, params=params, headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data and len(data) > 0:
                                    return {
                                        "found": True,
                                        "results": data,
                                        "confidence": 0.88,
                                        "source": f"funds_api_pattern_{list(params.keys())[0]}"
                                    }
                except Exception:
                    continue  # Try next pattern
            
            return {"found": False, "error": "No pattern matches", "confidence": 0.0}
                        
        except Exception as e:
            logger.error(f"Funds pattern search error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    def _remove_duplicate_funds(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate funds based on ISIN or scheme_code"""
        seen_identifiers = set()
        unique_results = []
        
        for fund in results:
            # Create identifier based on available fields
            identifier = None
            if isinstance(fund, dict):
                # Check for ISIN first (most reliable)
                if "isin" in fund and fund["isin"]:
                    identifier = fund["isin"]
                elif "scheme_code" in fund and fund["scheme_code"]:
                    identifier = fund["scheme_code"]
                elif "scheme_name" in fund and fund["scheme_name"]:
                    identifier = fund["scheme_name"].strip().upper()
                
                if identifier and identifier not in seen_identifiers:
                    seen_identifiers.add(identifier)
                    unique_results.append(fund)
                elif identifier is None:
                    # If no identifier found, include it anyway
                    unique_results.append(fund)
        
        return unique_results
    
    async def call_web_scraper(self, queries: List[str], intent: IntentType) -> Dict[str, Any]:
        """Call general web scraper for fund information"""
        
        try:
            return await self._call_tavily_api(queries, intent)
        except Exception as e:
            logger.error(f"Web scraping error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    async def call_tavily_search(self, query: str) -> Dict[str, Any]:
        """Search using Tavily API for mutual fund information"""
        
        try:
            return await self._call_tavily_api([query], IntentType.FUND_QUERY)
        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    async def _call_tavily_api(self, queries: List[str], intent: IntentType) -> Dict[str, Any]:
        """Call Tavily API for web search results"""
        
        if not queries:
            return {"found": False, "error": "No queries provided", "confidence": 0.0}
        
        # Combine queries into a single effective search query
        search_query = " ".join(queries)
        
        # Add context based on intent
        if intent == IntentType.FUND_QUERY:
            search_query += " mutual fund India NAV details performance"
        elif intent == IntentType.COMPARE_FUNDS:
            search_query += " mutual fund comparison India performance metrics"
        elif intent == IntentType.GENERAL_INFO:
            search_query += " mutual fund investment advice strategies India"
        
        try:
            # Ensure API key is properly loaded
            api_key = self.config.TAVILY_API_KEY
            if not api_key or api_key == "":
                return {"found": False, "error": "Tavily API key not configured", "confidence": 0.0}
            
            # Try different header formats that might work
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "Authorization": f"Bearer {api_key}",  # Alternative format
            }
            
            payload = {
                "query": search_query,
                "search_depth": "advanced",
                "include_domains": self.config.PREFERRED_DOMAINS,
                "max_results": self.config.MAX_WEB_SOURCES
            }
            
            logger.info(f"Making Tavily API call with query: {search_query}")
            logger.info(f"Using API key: {api_key[:10]}...{api_key[-5:]}")  # Log partial key for debugging
            logger.info(f"Tavily payload: {payload}")
            
            # Try different payload configurations for better compatibility
            basic_payload = {
                "query": search_query,
                "max_results": self.config.MAX_WEB_SOURCES
            }
            
            # First attempt with full payload
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.WEB_SCRAPE_TIMEOUT)) as session:
                # Try the original payload first
                async with session.post("https://api.tavily.com/search", headers=headers, json=payload) as response:
                    logger.info(f"Tavily API response status (full payload): {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Tavily API response: {result}")
                        
                        if result.get("results"):
                            # Format results
                            formatted_results = []
                            for item in result.get("results", []):
                                formatted_results.append({
                                    "title": item.get("title", ""),
                                    "content": item.get("content", ""),
                                    "url": item.get("url", ""),
                                    "score": item.get("relevance_score", 0)
                                })
                            
                            logger.info(f"Tavily formatted {len(formatted_results)} results")
                            return {
                                "found": True,
                                "results": formatted_results,
                                "confidence": result.get("results")[0].get("relevance_score", 0.75) if result.get("results") else 0.0,
                                "source": "TAVILY_API",
                                "retrieved_at": datetime.now().isoformat()
                            }
                    
                    # If full payload fails, try basic payload
                    elif response.status == 401:
                        logger.warning("Full payload failed with 401, trying basic payload...")
                        async with session.post("https://api.tavily.com/search", headers=headers, json=basic_payload) as basic_response:
                            logger.info(f"Tavily API response status (basic payload): {basic_response.status}")
                            
                            if basic_response.status == 200:
                                result = await basic_response.json()
                                logger.info(f"Tavily API response (basic): {result}")
                                
                                if result.get("results"):
                                    # Format results
                                    formatted_results = []
                                    for item in result.get("results", []):
                                        formatted_results.append({
                                            "title": item.get("title", ""),
                                            "content": item.get("content", ""),
                                            "url": item.get("url", ""),
                                            "score": item.get("relevance_score", 0)
                                        })
                                    
                                    logger.info(f"Tavily formatted {len(formatted_results)} results (basic)")
                                    return {
                                        "found": True,
                                        "results": formatted_results,
                                        "confidence": result.get("results")[0].get("relevance_score", 0.75) if result.get("results") else 0.0,
                                        "source": "TAVILY_API",
                                        "retrieved_at": datetime.now().isoformat()
                                    }
                            else:
                                error_text = await basic_response.text()
                                logger.error(f"Tavily API error status {basic_response.status} (basic): {error_text}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Tavily API error status {response.status}: {error_text}")
                        
                return {"found": False, "error": "No results from Tavily API", "confidence": 0.0}
                        
        except Exception as e:
            logger.error(f"Tavily API error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
        
        # This would implement web scraping from preferred domains
        # For now, return a placeholder
        return {
            "found": False,
            "error": "Web scraper not yet implemented",
            "confidence": 0.0,
            "sources": []
        }
    
    async def call_moonshot_llm(self, user_input: str, intent: IntentType, 
                           params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call Moonshot AI LLM for synthesis or general questions"""
        
        if params is None:
            params = {}
        
        try:
            # Import OpenAI client for Moonshot
            try:
                import openai
                
                client = openai.AsyncOpenAI(
                    api_key=self.config.MOONSHOT_API_KEY,
                    base_url=self.config.MOONSHOT_BASE_URL
                )
                
                # Prepare messages for Moonshot
                system_prompt = """You are a knowledgeable financial assistant specializing in Indian mutual funds. 
                Provide accurate, helpful information about mutual funds, SIPs, NAVs, and investment concepts.
                Keep responses concise but informative. Always mention that this is general information 
                and users should verify current data from official sources.
                
                If asked about specific fund data (NAV, performance, holdings), remind users that you provide 
                general information and they should check official sources for current data."""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
                
                # Call Moonshot API
                response = await client.chat.completions.create(
                    model=self.config.MOONSHOT_MODEL,
                    messages=messages,
                    temperature=self.config.MOONSHOT_TEMPERATURE,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                
                return {
                    "found": True,
                    "type": "llm_response",
                    "content": content,
                    "confidence": 0.8,
                    "source": "MOONSHOT_LLM",
                    "retrieved_at": datetime.now().isoformat()
                }
                
            except ImportError:
                logger.warning("OpenAI package not available, using simulated response")
                # Fallback to simulated response
                simulated_response = await self._simulate_moonshot_response(user_input, intent)
                
                return {
                    "found": True,
                    "type": "llm_response", 
                    "content": simulated_response,
                    "confidence": 0.8,
                    "source": "MOONSHOT_LLM_SIMULATED",
                    "retrieved_at": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Moonshot LLM error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    async def _simulate_moonshot_response(self, user_input: str, intent: IntentType) -> str:
        """Simulate Moonshot response (replace with actual Moonshot API call)"""
        
        if "greeting" in intent.intent.value or "hello" in user_input.lower():
            return """Hello! I'm your Mutual Funds Assistant. I can help you with:

• **Fund Information** - Details about specific mutual funds
• **NAV Data** - Current and historical Net Asset Values  
• **Performance Analysis** - Returns and growth data
• **Fund Comparisons** - Compare different funds
• **General Questions** - Mutual fund concepts and processes

What would you like to know about mutual funds today?"""
        
        if "what is" in user_input.lower() and ("nav" in user_input.lower() or "net asset value" in user_input.lower()):
            return """**Net Asset Value (NAV)** is the per-unit market value of a mutual fund.

**Key Points:**
• NAV = (Total Asset Value - Liabilities) ÷ Number of Units Outstanding
• Updated daily after market closure
• Used for buying and selling fund units
• Higher NAV doesn't mean better performance

**Example:** If a fund has ₹100 crores in assets, ₹2 crores in liabilities, and 98 lakh units outstanding:
NAV = (100 - 2) ÷ 0.98 = ₹100 per unit

Would you like to check the current NAV of a specific fund?"""
        
        # Default response for general queries
        return """I'd be happy to help you with mutual fund information! 

To give you the most accurate and current data, could you please specify:
• **Fund name** (e.g., "Axis Bluechip Fund")
• **What information** you need (NAV, performance, holdings, etc.)

This helps me fetch the latest data from official sources."""

    async def call_db_api_by_isin(self, isin: str) -> Dict[str, Any]:
        """Comprehensive search by ISIN across all fund endpoints"""
        
        try:
            # Search all ISIN-specific endpoints in parallel
            search_tasks = [
                self._get_fund_by_isin(isin),
                self._get_fund_complete_data(isin),
                self._get_fund_factsheet(isin),
                self._get_fund_returns(isin),
                self._get_fund_holdings(isin),
                self._get_fund_nav(isin),
                self._get_bse_scheme_by_isin(isin)
            ]
            
            # Execute all searches concurrently
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Aggregate all successful results
            comprehensive_data = {}
            sources_used = []
            
            endpoint_names = [
                "fund_details", "complete_data", "factsheet", 
                "returns", "holdings", "nav_history", "bse_scheme"
            ]
            
            for i, result in enumerate(results):
                endpoint_name = endpoint_names[i]
                if isinstance(result, dict) and result.get("found", False):
                    comprehensive_data[endpoint_name] = result.get("results", {})
                    sources_used.append(f"{endpoint_name}_api")
            
            if comprehensive_data:
                return {
                    "found": True,
                    "results": comprehensive_data,
                    "confidence": 0.98,  # Highest confidence for ISIN-based search
                    "sources": sources_used,
                    "search_type": "comprehensive_isin_search",
                    "isin": isin,
                    "retrieved_at": datetime.now().isoformat()
                }
            else:
                return {
                    "found": False,
                    "error": f"No data found for ISIN {isin} across all endpoints",
                    "confidence": 0.0
                }
                        
        except Exception as e:
            logger.error(f"Comprehensive ISIN search error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}
    
    async def _get_fund_by_isin(self, isin: str) -> Dict[str, Any]:
        """Get fund details by ISIN from /api/funds/{isin}"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "funds_by_isin"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_fund_complete_data(self, isin: str) -> Dict[str, Any]:
        """Get complete fund data from /api/funds/{isin}/complete"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}/complete"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "complete_fund_data"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_fund_factsheet(self, isin: str) -> Dict[str, Any]:
        """Get fund factsheet from /api/funds/{isin}/factsheet"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}/factsheet"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "factsheet"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_fund_returns(self, isin: str) -> Dict[str, Any]:
        """Get fund returns from /api/funds/{isin}/returns"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}/returns"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "returns_data"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_fund_holdings(self, isin: str) -> Dict[str, Any]:
        """Get fund holdings from /api/funds/{isin}/holdings"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}/holdings"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "holdings_data"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_fund_nav(self, isin: str) -> Dict[str, Any]:
        """Get fund NAV history from /api/funds/{isin}/nav"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/funds/{isin}/nav"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "nav_history"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    async def _get_bse_scheme_by_isin(self, isin: str) -> Dict[str, Any]:
        """Get BSE scheme by ISIN from /api/bse-schemes/by-isin/{isin}"""
        try:
            url = f"{self.config.PRODUCTION_API_BASE}/api/bse-schemes/by-isin/{isin}"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"found": True, "results": data, "source": "bse_by_isin"}
                    return {"found": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"found": False, "error": str(e)}

    async def call_bse_schemes_api(self, scheme_name: Optional[str] = None,
                                  isin: Optional[str] = None,
                                  unique_no: Optional[str] = None) -> Dict[str, Any]:
        """Call BSE schemes API for additional fund data"""
        
        try:
            base_url = f"{self.config.PRODUCTION_API_BASE}/api/bse-schemes/"
            
            if unique_no:
                url = f"{base_url}{unique_no}"
                params = None
            elif isin:
                url = f"{base_url}by-isin/{isin}"
                params = None
            else:
                url = base_url
                params = {}
                if scheme_name:
                    params["scheme_name"] = scheme_name
                params["active_only"] = "true"  # Fix: Use string instead of boolean
            
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if we have schemes data
                        if isinstance(data, dict) and "schemes" in data:
                            schemes = data["schemes"]
                            if schemes and len(schemes) > 0:
                                return {
                                    "found": True,
                                    "results": schemes,
                                    "confidence": 0.95,  # Very high confidence for BSE data
                                    "source": "BSE_SCHEMES_API",
                                    "retrieved_at": datetime.now().isoformat(),
                                    "pagination": data.get("pagination", {})
                                }
                            else:
                                return {
                                    "found": False,
                                    "error": "No schemes found in BSE API",
                                    "confidence": 0.0
                                }
                        else:
                            # Single scheme result
                            return {
                                "found": True,
                                "results": [data] if isinstance(data, dict) else data,
                                "confidence": 0.95,
                                "source": "BSE_SCHEMES_API",
                                "retrieved_at": datetime.now().isoformat()
                            }
                    else:
                        return {
                            "found": False,
                            "error": f"BSE API returned status {response.status}",
                            "confidence": 0.0
                        }
                        
        except Exception as e:
            logger.error(f"BSE schemes API error: {str(e)}")
            return {"found": False, "error": str(e), "confidence": 0.0}

    # ========== NEW DEEP SEARCH METHODS ==========
    
    async def _deep_exact_search(self, fund_name: str, metric: Optional[str]) -> Dict[str, Any]:
        """
        Phase 1: Exact match search across ALL available endpoints
        """
        
        # Search all endpoints in parallel for maximum thoroughness
        search_tasks = [
            self._search_funds_api(fund_name, metric),
            self._search_bse_schemes_api(fund_name)
        ]
        
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Combine all successful results
            combined_results = []
            highest_confidence = 0.0
            
            for i, result in enumerate(results):
                if isinstance(result, dict) and result.get("found") and result.get("results"):
                    combined_results.extend(result.get("results", []))
                    highest_confidence = max(highest_confidence, result.get("confidence", 0.0))
                    logger.info(f"Endpoint {i+1} found {len(result.get('results', []))} results")
            
            if combined_results:
                # Remove duplicates and sort by relevance
                unique_results = self._remove_duplicate_funds(combined_results)
                return {
                    "found": True,
                    "results": unique_results[:20],  # Limit to top 20 results
                    "confidence": highest_confidence,
                    "source": "DEEP_DB_SEARCH_EXACT",
                    "search_phase": "exact_match"
                }
                
        except Exception as e:
            logger.error(f"Error in deep exact search: {e}")
            
        return {"found": False, "error": "No exact matches found", "confidence": 0.0}
        
    async def _intelligent_keyword_search(self, fund_name: str, metric: Optional[str]) -> Dict[str, Any]:
        """
        Phase 2: Intelligent keyword extraction and strategic searching
        """
        
        # Extract meaningful keywords from the fund name
        keywords = self._extract_intelligent_keywords(fund_name)
        logger.info(f"Extracted keywords: {keywords}")
        
        combined_results = []
        
        # Search with each significant keyword
        for keyword in keywords:
            if len(keyword) > 2:  # Skip very short keywords
                logger.info(f"Searching with keyword: {keyword}")
                keyword_result = await self._search_with_keyword(keyword, metric)
                
                if keyword_result.get("found") and keyword_result.get("results"):
                    combined_results.extend(keyword_result.get("results", []))
                    
        if combined_results:
            # Score results based on relevance to original query
            scored_results = self._score_results_relevance(combined_results, fund_name)
            unique_results = self._remove_duplicate_funds(scored_results)
            
            return {
                "found": True,
                "results": unique_results[:15],
                "confidence": 0.8,
                "source": "DEEP_DB_SEARCH_KEYWORDS",
                "search_phase": "keyword_extraction"
            }
            
        return {"found": False, "error": "No keyword matches found", "confidence": 0.0}

    async def _fuzzy_match_search(self, fund_name: str, metric: Optional[str]) -> Dict[str, Any]:
        """
        Phase 3: Fuzzy matching and partial search strategies
        """
        
        logger.info("Starting fuzzy matching search")
        all_fuzzy_results = []
        search_variations = []
        
        # Create search variations for fuzzy matching
        words = fund_name.split()
        
        # Generate partial matches
        if len(words) > 1:
            for i in range(len(words)):
                for j in range(i + 1, len(words) + 1):
                    partial_phrase = " ".join(words[i:j])
                    if len(partial_phrase) > 2:  # Avoid very short phrases
                        search_variations.append(partial_phrase)
        
        # Add single word searches for meaningful words
        meaningful_words = [word for word in words if len(word) > 3 and word.lower() not in ['fund', 'plan', 'scheme']]
        search_variations.extend(meaningful_words)
        
        # Remove duplicates and sort by length (longer phrases first)
        search_variations = sorted(list(set(search_variations)), key=len, reverse=True)[:5]
        
        logger.info(f"Fuzzy search variations: {search_variations}")
        
        for variation in search_variations:
            try:
                logger.info(f"Fuzzy searching with variation: {variation}")
                result = await self._search_single_api("funds", {"scheme_name": variation})
                
                if result.get("found") and result.get("results"):
                    # Score based on similarity to original query
                    scored_results = []
                    for fund in result.get("results", []):
                        similarity_score = self._calculate_fuzzy_similarity(fund_name.lower(), fund.get("scheme_name", "").lower())
                        if similarity_score > 0.3:  # Minimum similarity threshold
                            fund["fuzzy_score"] = similarity_score
                            fund["search_variation"] = variation
                            scored_results.append(fund)
                    
                    all_fuzzy_results.extend(scored_results)
                    
            except Exception as e:
                logger.error(f"Error in fuzzy search with {variation}: {e}")
                continue
        
        if all_fuzzy_results:
            # Sort by fuzzy score
            all_fuzzy_results.sort(key=lambda x: x.get("fuzzy_score", 0), reverse=True)
            unique_results = self._remove_duplicate_funds(all_fuzzy_results)
            
            return {
                "found": True,
                "results": unique_results[:10],
                "confidence": 0.6,
                "source": "DEEP_DB_SEARCH_FUZZY",
                "search_phase": "fuzzy_matching"
            }
            
        return {"found": False, "error": "No fuzzy matches found", "confidence": 0.0}

    def _calculate_fuzzy_similarity(self, query: str, fund_name: str) -> float:
        """
        Calculate fuzzy similarity between query and fund name
        """
        try:
            # Simple similarity calculation
            query_words = set(query.lower().split())
            fund_words = set(fund_name.lower().split())
            
            # Calculate word overlap
            intersection = len(query_words & fund_words)
            union = len(query_words | fund_words)
            
            if union == 0:
                return 0.0
                
            jaccard_similarity = intersection / union
            
            # Bonus for substring matches
            substring_bonus = 0.0
            for q_word in query_words:
                for f_word in fund_words:
                    if q_word in f_word or f_word in q_word:
                        substring_bonus += 0.1
            
            return min(1.0, jaccard_similarity + substring_bonus)
            
        except Exception as e:
            logger.error(f"Error calculating fuzzy similarity: {e}")
            return 0.0
        
    def _extract_intelligent_keywords(self, fund_name: str) -> List[str]:
        """
        Intelligently extract meaningful keywords from fund name
        """
        
        # Common words to filter out
        stop_words = {"fund", "mutual", "scheme", "direct", "growth", "dividend", "plan", "option", "regular"}
        
        # Split and clean
        words = fund_name.replace("-", " ").replace("_", " ").split()
        keywords = []
        
        for word in words:
            cleaned_word = word.strip().upper()
            if len(cleaned_word) > 2 and cleaned_word.lower() not in stop_words:
                keywords.append(cleaned_word)
                
        # Also add the first word and last word as potential key identifiers
        if words:
            keywords.append(words[0].strip().upper())
            if len(words) > 1:
                keywords.append(words[-1].strip().upper())
                
        return list(set(keywords))  # Remove duplicates
        
    async def _search_with_keyword(self, keyword: str, metric: Optional[str]) -> Dict[str, Any]:
        """
        Search with a specific keyword across multiple endpoints
        """
        
        # Try all search endpoints with this keyword
        search_tasks = [
            self._search_funds_api(keyword, metric),
            self._search_bse_schemes_api(keyword)
        ]
        
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            combined_results = []
            for result in results:
                if isinstance(result, dict) and result.get("found") and result.get("results"):
                    combined_results.extend(result.get("results", []))
                    
            if combined_results:
                return {
                    "found": True,
                    "results": combined_results,
                    "confidence": 0.75,
                    "source": "KEYWORD_SEARCH"
                }
                
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            
        return {"found": False, "error": f"No results for keyword: {keyword}", "confidence": 0.0}
        
    def _score_results_relevance(self, results: List[dict], original_query: str) -> List[dict]:
        """
        Score results based on relevance to original query
        """
        
        query_words = set(original_query.upper().split())
        
        for result in results:
            scheme_name = result.get("scheme_name", "").upper()
            amc_name = result.get("amc_name", "").upper()
            
            # Count matching words
            scheme_words = set(scheme_name.split())
            amc_words = set(amc_name.split())
            
            matches = len(query_words.intersection(scheme_words.union(amc_words)))
            result["relevance_score"] = matches / max(len(query_words), 1)
            
        # Sort by relevance score
        return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
    def _remove_duplicate_funds(self, results: List[dict]) -> List[dict]:
        """
        Remove duplicate fund entries based on scheme name and AMC
        """
        
        seen = set()
        unique_results = []
        
        for result in results:
            scheme_name = result.get("scheme_name", "")
            amc_name = result.get("amc_name", "")
            identifier = f"{scheme_name}_{amc_name}".lower()
            
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(result)
                
        return unique_results

    async def _search_single_api(self, endpoint: str, params: dict) -> Dict[str, Any]:
        """
        Search a single API endpoint with given parameters
        """
        try:
            if endpoint == "funds":
                url = f"{self.config.PRODUCTION_API_BASE}/api/funds/"
                logger.info(f"Searching {endpoint} API with URL: {url}, params: {params}")
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)) as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if isinstance(data, dict) and "data" in data:
                                results = data["data"]
                                if results:
                                    return {
                                        "found": True,
                                        "results": results[:20],
                                        "confidence": 0.7,
                                        "source": "SINGLE_API_SEARCH"
                                    }
            
            return {"found": False, "error": "No results found", "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"Error in single API search: {e}")
            return {"found": False, "error": str(e), "confidence": 0.0}

    async def _amc_level_search(self, fund_name: str, metric: Optional[str]) -> Dict[str, Any]:
        """
        Phase 4: AMC-level and category-based search
        """
        logger.info("Starting AMC-level search")
        
        try:
            # Extract potential AMC names from the query
            amc_keywords = ["HDFC", "ICICI", "SBI", "Axis", "Kotak", "DSP", "Edelweiss", "Aditya Birla", "Franklin", "Nippon"]
            found_amc = None
            
            for amc in amc_keywords:
                if amc.lower() in fund_name.lower():
                    found_amc = amc
                    break
            
            if found_amc:
                logger.info(f"Found AMC keyword: {found_amc}")
                result = await self._search_single_api("funds", {"scheme_name": found_amc})
                
                if result.get("found"):
                    return {
                        "found": True,
                        "results": result.get("results", [])[:10],
                        "confidence": 0.5,
                        "source": "AMC_LEVEL_SEARCH",
                        "search_phase": "amc_matching"
                    }
            
            # Fallback: search for popular fund categories
            categories = ["Equity", "Debt", "Hybrid", "Index", "ELSS"]
            for category in categories:
                if category.lower() in fund_name.lower():
                    logger.info(f"Found category keyword: {category}")
                    result = await self._search_single_api("funds", {"scheme_name": category})
                    
                    if result.get("found"):
                        return {
                            "found": True,
                            "results": result.get("results", [])[:10],
                            "confidence": 0.4,
                            "source": "CATEGORY_LEVEL_SEARCH",
                            "search_phase": "category_matching"
                        }
            
            return {"found": False, "error": "No AMC or category matches found", "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"Error in AMC-level search: {e}")
            return {"found": False, "error": str(e), "confidence": 0.0}

    def _extract_fund_name_from_query(self, user_query: str) -> str:
        """
        Extract actual fund/AMC name from natural language queries
        Smart extraction without hardcoded patterns
        """
        query_lower = user_query.lower().strip()
        
        # Known AMC/Fund house names (common ones)
        amc_names = [
            'dsp', 'axis', 'hdfc', 'sbi', 'icici', 'edelweiss', 'aditya birla', 'nippon',
            'kotak', 'franklin', 'invesco', 'l&t', 'tata', 'motilal oswal', 'mirae',
            'uti', 'reliance', 'principal', 'pgim', 'hsbc', 'canara', 'union',
            'quantum', 'idfc', '360 one', 'baroda', 'bajaj', 'bnp', 'sundaram'
        ]
        
        # Find AMC name in query
        for amc in amc_names:
            if amc in query_lower:
                logger.info(f"Found AMC '{amc}' in query: '{user_query}'")
                return amc
        
        # Look for specific fund name patterns
        words = user_query.split()
        
        # If query is very specific fund name, return as is
        if len(words) <= 4 and any(word.lower() in ['fund', 'mutual', 'scheme'] for word in words):
            return user_query.strip()
        
        # For longer queries, try to extract meaningful parts
        # Remove common question words
        filtered_words = []
        skip_words = ['give', 'complete', 'information', 'about', 'tell', 'me', 'show', 'get', 'find', 'what', 'is', 'the']
        
        for word in words:
            if word.lower() not in skip_words:
                filtered_words.append(word)
        
        # If we found something meaningful, return it
        if filtered_words:
            extracted = ' '.join(filtered_words)
            logger.info(f"Extracted query parts: '{extracted}' from '{user_query}'")
            return extracted
        
        # Fallback: return original query
        logger.info(f"No extraction applied, using original: '{user_query}'")
        return user_query
