# AI Hedge Fund - Tools and Custom Agents Feature

## Overview

This feature adds N8N-like capabilities to the AI Hedge Fund application, allowing users to create custom agents with access to various tools, starting with Alpaca trading API integration.

## Features

### 1. Tool Registry System
- Centralized tool management
- Dynamic tool registration
- Tool categorization for easy discovery
- Tool schema generation for LLM compatibility

### 2. Alpaca Trading Tools
The following Alpaca tools are available:

#### Account Tools
- `get_account` - Get account information (cash, buying power, equity)
- `get_portfolio_history` - Get portfolio performance history

#### Portfolio Tools  
- `get_positions` - Get current positions (optionally filtered by symbols)
- `get_portfolio_for_agents` - Get portfolio data formatted for agent system

#### Trading Tools
- `place_market_order` - Place market buy/sell orders
- `place_limit_order` - Place limit orders with specific prices
- `get_orders` - Get order list with status filtering
- `cancel_order` - Cancel orders by ID

#### Market Data Tools
- `get_bars` - Get historical price data
- `get_latest_quote` - Get current bid/ask quotes
- `get_clock` - Get market status (open/closed)

### 3. Custom Agent Nodes
- Visual node in React Flow for creating custom agents
- Tool selection interface with categorized tools
- Real-time configuration and testing
- System prompt customization

### 4. Enhanced Portfolio Manager
- Portfolio manager now supports tool integration
- Default tools for real-time market data access
- Enhanced decision-making with live data

## Setup

### Environment Variables
Add these to your `.env` file:
```env
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_PAPER=true  # Use paper trading by default
```

### Installation
The required dependencies have been added to `requirements.txt`:
- `alpaca-py` - Alpaca trading API client
- `termcolor` - Colored terminal output

## Usage

### Creating a Custom Agent

1. **From the UI:**
   - Drag the "Custom Agent" node from the sidebar
   - Click "Configure" to set up the agent
   - Enter agent name and description
   - Select tools from categorized list
   - Optionally add a custom system prompt
   - Click "Save Agent"

2. **Via API:**
   ```bash
   curl -X POST http://localhost:8000/api/tools/agents \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Market Analyst",
       "description": "Analyzes market conditions",
       "model": "gpt-4o",
       "tools": ["get_latest_quote", "get_bars", "get_clock"],
       "system_prompt": "You are a market analyst..."
     }'
   ```

### Using Tools Directly

```bash
# Get account information
curl http://localhost:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_account",
    "parameters": {}
  }'

# Get latest quote
curl http://localhost:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_latest_quote",
    "parameters": {"symbol": "AAPL"}
  }'
```

### Tool Categories

Tools are organized into categories:
- `alpaca_account` - Account management
- `alpaca_portfolio` - Portfolio information
- `alpaca_trading` - Order execution
- `alpaca_market_data` - Market data retrieval

## API Endpoints

### Tool Management
- `GET /api/tools/` - List all available tools
- `GET /api/tools/categories` - Get tools grouped by category
- `GET /api/tools/schema/{tool_name}` - Get schema for specific tool
- `POST /api/tools/execute` - Execute a tool

### Agent Management
- `POST /api/tools/agents` - Create custom agent
- `GET /api/tools/agents` - List custom agents
- `POST /api/tools/agents/{agent_name}/analyze` - Run analysis with agent
- `DELETE /api/tools/agents/{agent_name}` - Delete custom agent

## Architecture

### Backend Components

1. **Tool Registry (`src/tools/tool_registry.py`)**
   - Central registry for all tools
   - Tool validation and execution
   - Schema generation for LLMs

2. **Alpaca Tools (`src/tools/alpaca_tools.py`)**
   - Implementation of all Alpaca API integrations
   - Error handling and data formatting

3. **Base Agent (`src/agents/base_agent.py`)**
   - Abstract base class with tool support
   - Tool execution methods
   - LangChain integration

4. **API Routes (`app/backend/routes/tools.py`)**
   - RESTful endpoints for tool/agent management
   - Request validation

### Frontend Components

1. **Custom Agent Node (`app/frontend/src/nodes/components/custom-agent-node.tsx`)**
   - React component for custom agents
   - Tool selection UI
   - Real-time configuration

2. **Node Integration**
   - Added to node types registry
   - Drag-and-drop support
   - Visual workflow integration

## Future Enhancements

1. **Additional Tool Integrations**
   - Yahoo Finance API
   - News APIs
   - Technical indicators
   - Economic data sources

2. **Advanced Features**
   - Tool chaining capabilities
   - Conditional tool execution
   - Tool result caching
   - Tool usage analytics

3. **UI Improvements**
   - Tool testing interface
   - Visual tool builder
   - Tool documentation viewer
   - Performance monitoring

## Troubleshooting

### Common Issues

1. **Alpaca API Errors**
   - Ensure API keys are correctly set in `.env`
   - Check if using paper trading vs live
   - Verify market hours for trading operations

2. **Tool Execution Failures**
   - Check tool parameters match schema
   - Verify tool is enabled in registry
   - Review error logs for details

3. **Custom Agent Issues**
   - Ensure unique agent names
   - Verify selected tools exist
   - Check model availability

## Contributing

To add new tools:

1. Implement tool functions in appropriate module
2. Register tools in `tool_registry.py`
3. Add tool category if needed
4. Update documentation
5. Add tests for new tools

## License

This feature is part of the AI Hedge Fund project and follows the same license terms.