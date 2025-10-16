# Interactive Mutual Funds Agent

An intelligent, conversational mutual funds assistant built with LangChain zero-shot approach, Groq LLM, and comprehensive data sources.

## 🌟 Features

### 🤖 Intelligent Agent Behavior
- **Zero-shot reasoning** using LangChain methodology
- **Intent recognition** with sentiment analysis
- **Interactive confirmations** for ambiguous queries
- **Multi-source data retrieval** with smart fallbacks

### 📊 Data Sources
- **Production API** (`http://34.122.133.139:4000`) - Primary fund database
- **AMFI Official Data** - Authoritative NAV and scheme data
- **BSE Scheme Master** - Comprehensive scheme information
- **Web Scraping Fallback** - From trusted financial domains

### 💬 Conversational Features
- **Context awareness** across conversation
- **Personalized responses** with user name recognition
- **Sentiment adaptation** (empathetic, professional, urgent responses)
- **Dynamic follow-ups** to avoid repetition

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Interactive Agent
```bash
python main.py
```

### 3. Try Demo Modes
```bash
# Automated demo with sample queries
python demo.py --demo

# Interactive chat session
python demo.py --interactive

# Test API connectivity
python demo.py --test-api
```

## 🎯 Example Interactions

### Simple Fund Query
```
User: "Tell me about Axis fund"
Agent: "I found multiple Axis funds. Do you mean:
        1. Axis Bluechip Fund
        2. Axis Focused 25 Fund  
        3. Axis Midcap Fund
        Which one interests you?"

User: "Axis Bluechip Fund"
Agent: [Provides complete fund details with NAV, manager, AUM, etc.]
```

### NAV Request
```
User: "What's the current NAV of HDFC Top 100?"
Agent: [Fetches latest NAV from API/AMFI with source citation]
```

### General Questions
```
User: "What is SIP?"
Agent: [Uses Groq LLM to explain SIP concept clearly]
```

## 🏗️ Architecture

### Agent Decision Flow
```
User Input → Intent Parser → Agent Decision → Tool Selection → Response Formatter
```

### Tool Hierarchy (Automatic Fallback)
1. **DB API** (Primary) - Structured fund database
2. **AMFI Scraping** (Secondary) - Official regulatory data  
3. **Web Scraping** (Tertiary) - Trusted financial websites
4. **Groq LLM** (Synthesis) - General questions and response formatting

### Key Components

#### 🧠 `MutualFundsAgent` (Core)
- Zero-shot decision making
- Tool orchestration
- Session management

#### 🎯 `IntentParser`
- Pattern-based intent recognition
- Entity extraction (fund names, metrics, periods)
- Sentiment analysis
- Clarity assessment

#### 🔧 `ToolOrchestrator` 
- API client management
- Web scraping coordination
- Groq LLM integration
- Error handling and retries

#### 📝 `ResponseFormatter`
- Structured response formatting
- Source citation
- Confidence scoring
- Metadata generation

## 🛠️ Configuration

### Environment Variables
```bash
# Optional overrides (defaults provided)
export PRODUCTION_API_BASE="http://34.122.133.139:4000"
export GROQ_API_KEY="your-groq-api-key"
export GROQ_MODEL="llama-3.3-70b-versatile"
export CONFIDENCE_THRESHOLD="0.75"
```

### API Endpoints Used

#### Funds API
- `GET /api/funds` - All funds with filtering
- `GET /api/funds/{isin}` - Specific fund by ISIN
- `GET /api/funds/{isin}/complete` - Comprehensive data
- `GET /api/funds/{isin}/factsheet` - Fund factsheet
- `GET /api/funds/{isin}/returns` - Performance returns
- `GET /api/funds/{isin}/holdings` - Portfolio holdings
- `GET /api/funds/{isin}/nav` - NAV history

#### BSE Scheme Master API
- `GET /api/bse-schemes` - BSE schemes with filtering
- `GET /api/bse-schemes/{unique_no}` - Scheme by unique number
- `GET /api/bse-schemes/by-isin/{isin}` - Scheme by ISIN

## 📋 Response Format

Every response includes:

1. **Dynamic Greeting** (sentiment-adapted)
2. **TL;DR** (one-sentence summary)
3. **Key Answer** (2-4 bullet points with sources)
4. **Detailed Explanation** (multiple subsections)
5. **Evidence & Sources** (numbered list with confidence scores)
6. **Suggested Next Steps** (actionable recommendations)
7. **Follow-up Prompt** (dynamic, non-repetitive)
8. **Source Rationale** (why these sources were chosen)
9. **Confidence Score** (with explanation)
10. **Compliance Disclaimer**
11. **Metadata JSON** (method, tools, sources, confidence)

## 🔐 Security & Compliance

- **No PII Collection** - Agent doesn't request passwords or personal data
- **No Transactions** - Redirects to secure authentication for any transaction requests
- **Source Attribution** - Every fact includes source and retrieval timestamp
- **Confidence Scoring** - Transparent about data reliability
- **Compliance Disclaimers** - Clear that responses are not financial advice

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test specific components
python -m pytest tests/test_intent_parser.py -v
python -m pytest tests/test_tools.py -v
```

## 📝 Development

### Adding New Intent Types
1. Add to `IntentType` enum in `intent_parser.py`
2. Add patterns to `intent_patterns` dict
3. Update decision logic in `core.py`

### Adding New Data Sources
1. Add method to `ToolOrchestrator` 
2. Update decision tree in `MutualFundsAgent`
3. Add source formatting in `ResponseFormatter`

### Customizing Responses
- Modify `ResponseFormatter` for different output formats
- Adjust `AgentConfig` for behavior tuning
- Update system prompts in `tools.py`

## 🔄 Roadmap

- [ ] **Enhanced Web Scraping** - More financial websites
- [ ] **Real-time Data Feeds** - Live market data integration
- [ ] **Portfolio Analysis** - Multi-fund portfolio insights
- [ ] **Recommendation Engine** - AI-powered fund suggestions
- [ ] **FastAPI Backend** - REST API for web/mobile apps
- [ ] **Streamlit UI** - Web interface for the agent

## 📞 Support

For issues or questions:
1. Check the logs for detailed error information
2. Test API connectivity using `python demo.py --test-api`
3. Verify your Groq API key is valid
4. Ensure internet connectivity for AMFI data

---

**Built with ❤️ using LangChain Zero-Shot methodology and Groq LLM**
