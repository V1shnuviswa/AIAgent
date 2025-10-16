# Mutual Funds Agent Frontend

A modern, responsive React frontend for the AI-powered Mutual Funds Agent.

## Features

- **Interactive Chat Interface**: Real-time conversation with the AI agent
- **Fund Search**: Comprehensive mutual fund search with detailed information
- **Fund Comparison**: Side-by-side comparison of multiple funds (coming soon)
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Real-time Updates**: WebSocket-based real-time communication
- **Modern UI**: Clean, professional interface built with Tailwind CSS

## Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API communication
- **WebSocket** for real-time chat
- **React Hot Toast** for notifications
- **Heroicons** for icons
- **React Markdown** for rich message formatting

## Prerequisites

- Node.js 16 or higher
- npm or yarn
- Backend API server running on `http://localhost:8000`

## Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to `http://localhost:3000`

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Layout.tsx      # Main layout wrapper
│   ├── ChatMessage.tsx # Chat message component
│   └── LoadingSpinner.tsx # Loading indicator
├── pages/              # Page components
│   ├── ChatPage.tsx    # Main chat interface
│   ├── FundSearchPage.tsx # Fund search functionality
│   ├── ComparePage.tsx # Fund comparison (coming soon)
│   └── AboutPage.tsx   # About and information
├── hooks/              # Custom React hooks
│   └── useChat.ts      # Chat functionality hook
├── utils/              # Utility functions
│   ├── api.ts         # API client and WebSocket manager
│   └── index.ts       # Helper functions
├── styles/             # CSS and styling
│   └── globals.css    # Global styles and Tailwind config
└── App.tsx            # Main app component
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## API Integration

The frontend communicates with the FastAPI backend through:

### REST API Endpoints
- `POST /api/session` - Create new chat session
- `POST /api/chat` - Send chat message
- `POST /api/funds/search` - Search mutual funds
- `GET /api/health` - Health check

### WebSocket Connection
- `ws://localhost:8000/ws/{session_id}` - Real-time chat

## Features Overview

### Chat Interface
- Natural language queries about mutual funds
- Real-time responses from AI agent
- Message history persistence
- Session management
- Markdown support for rich responses

### Fund Search
- Search by fund name
- Filter by search type (NAV, performance, etc.)
- Detailed fund information cards
- Performance metrics display
- Risk category indicators

### Responsive Design
- Mobile-first approach
- Collapsible sidebar navigation
- Touch-friendly interface
- Optimized for all screen sizes

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000` |

## Browser Support

- Chrome 88+
- Firefox 85+
- Safari 14+
- Edge 88+

## Performance Optimizations

- Code splitting with React.lazy()
- Image optimization
- Bundle size optimization
- Efficient re-rendering with React hooks
- WebSocket connection management

## Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Static Hosting
The `dist` folder can be deployed to any static hosting service:
- Vercel
- Netlify
- GitHub Pages
- AWS S3
- Cloudflare Pages

### Environment Configuration
Make sure to update `VITE_API_BASE_URL` for production deployment.

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow React hooks patterns
- Use functional components
- Implement proper error handling
- Add loading states for async operations

### Component Structure
- Keep components small and focused
- Use composition over inheritance
- Implement proper prop typing
- Handle loading and error states

### State Management
- Use React hooks for local state
- Implement custom hooks for reusable logic
- Keep state close to where it's used
- Use proper dependency arrays in useEffect

## Troubleshooting

### Common Issues

1. **Backend Connection Error**
   - Ensure backend server is running on `http://localhost:8000`
   - Check CORS settings in backend
   - Verify API endpoints are accessible

2. **WebSocket Connection Failed**
   - Check WebSocket URL configuration
   - Ensure backend supports WebSocket connections
   - Check browser developer tools for connection errors

3. **Build Errors**
   - Clear node_modules and reinstall dependencies
   - Check TypeScript configuration
   - Verify all imports are correct

### Debug Mode
Enable debug mode by adding to `.env`:
```env
VITE_DEBUG=true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Email: support@mfagent.com
- Documentation: [Link to docs]
- Issues: [GitHub Issues]
