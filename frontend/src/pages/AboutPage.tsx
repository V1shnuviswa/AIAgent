export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="mb-12 text-center">
        <div className="w-20 h-20 mx-auto mb-6 bg-primary-100 rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">About MF Agent</h1>
        <p className="text-xl text-gray-600">
          Your AI-powered mutual funds investment assistant
        </p>
      </div>

      {/* Main content */}
      <div className="prose prose-lg max-w-none">
        <div className="grid gap-8 md:grid-cols-2">
          {/* What is MF Agent */}
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">What is MF Agent?</h2>
            <p className="text-gray-600 mb-4">
              MF Agent is an intelligent chatbot designed to help investors make informed decisions about mutual funds in India. 
              Powered by advanced AI technology, it provides real-time fund information, performance analysis, and personalized investment advice.
            </p>
            <p className="text-gray-600">
              Whether you're a beginner looking to understand mutual funds or an experienced investor seeking detailed analytics, 
              MF Agent is here to assist you with comprehensive and up-to-date information.
            </p>
          </div>

          {/* Key Features */}
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Key Features</h2>
            <ul className="space-y-3 text-gray-600">
              <li className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Real-time NAV and fund performance data
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Comprehensive fund search and filtering
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                AI-powered investment recommendations
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Risk assessment and analysis
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Natural language query processing
              </li>
            </ul>
          </div>
        </div>

        {/* Technology Stack */}
        <div className="card mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Technology Stack</h2>
          <div className="grid gap-6 md:grid-cols-3">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">AI & Machine Learning</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Moonshot AI (Kimi K2 Instruct)</li>
                <li>• LangChain Framework</li>
                <li>• Zero-shot Learning</li>
                <li>• Natural Language Processing</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Data Sources</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Production Database API</li>
                <li>• Tavily Web Search</li>
                <li>• BSE Schemes Data</li>
                <li>• Real-time Fund Information</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Frontend & Backend</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• React with TypeScript</li>
                <li>• FastAPI Backend</li>
                <li>• WebSocket Real-time Chat</li>
                <li>• Tailwind CSS</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Data Sources & Accuracy */}
        <div className="card mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Data Sources & Accuracy</h2>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <div className="flex">
              <svg className="w-5 h-5 text-blue-400 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm text-blue-800">
                  <strong>Important:</strong> All fund data is sourced from reliable financial databases and updated regularly. 
                  However, market conditions change rapidly, and past performance doesn't guarantee future results.
                </p>
              </div>
            </div>
          </div>
          
          <p className="text-gray-600 mb-4">
            Our data comes from multiple sources to ensure accuracy and comprehensiveness:
          </p>
          
          <ul className="space-y-2 text-gray-600">
            <li className="flex items-start">
              <span className="font-medium mr-2">Primary Database:</span>
              Production API with real-time fund information including NAV, performance metrics, and fund details.
            </li>
            <li className="flex items-start">
              <span className="font-medium mr-2">Web Search:</span>
              Tavily API for latest news, analysis, and additional fund information from trusted financial websites.
            </li>
            <li className="flex items-start">
              <span className="font-medium mr-2">BSE Data:</span>
              Official BSE schemes database for comprehensive scheme information and validation.
            </li>
          </ul>
        </div>

        {/* Disclaimer */}
        <div className="card mt-8 bg-yellow-50 border-yellow-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
            <svg className="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Disclaimer
          </h2>
          <div className="text-sm text-gray-700 space-y-2">
            <p>
              MF Agent is designed for informational purposes only and should not be considered as professional financial advice. 
              Always consult with qualified financial advisors before making investment decisions.
            </p>
            <p>
              Past performance is not indicative of future results. Mutual fund investments are subject to market risks. 
              Please read all scheme-related documents carefully before investing.
            </p>
            <p>
              While we strive for accuracy, we cannot guarantee the completeness or timeliness of all data. 
              Always verify critical information from official sources before making investment decisions.
            </p>
          </div>
        </div>

        {/* Contact & Support */}
        <div className="card mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Contact & Support</h2>
          <p className="text-gray-600 mb-4">
            Have questions or feedback? We'd love to hear from you!
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex items-center text-gray-600">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span>support@mfagent.com</span>
            </div>
            
            <div className="flex items-center text-gray-600">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Version 1.0.0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
