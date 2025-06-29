from typing import Dict, Any, List, Callable, Optional
import inspect
from termcolor import colored
from pydantic import BaseModel, Field

class ToolParameter(BaseModel):
    """Definition of a tool parameter"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

class Tool(BaseModel):
    """Definition of a tool that can be used by agents"""
    name: str
    description: str
    function: str  # Module path to the function
    parameters: List[ToolParameter]
    category: str = "general"
    enabled: bool = True

class ToolRegistry:
    """Registry for managing tools available to agents"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._function_cache: Dict[str, Callable] = {}
        print(colored("Initializing Tool Registry...", "cyan"))
        
    def register_tool(self, tool: Tool) -> None:
        """Register a new tool"""
        print(colored(f"Registering tool: {tool.name}", "green"))
        self.tools[tool.name] = tool
        
    def register_function(self, func: Callable, category: str = "general", 
                         description: Optional[str] = None) -> None:
        """Register a function directly as a tool"""
        tool_name = func.__name__
        tool_description = description or func.__doc__ or f"Function {tool_name}"
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            param_type = "Any"
            if param.annotation != inspect.Parameter.empty:
                param_type = str(param.annotation)
                
            param_desc = f"Parameter {param_name}"
            required = param.default == inspect.Parameter.empty
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=param_desc,
                required=required,
                default=param.default if not required else None
            ))
        
        tool = Tool(
            name=tool_name,
            description=tool_description,
            function=f"{func.__module__}.{func.__name__}",
            parameters=parameters,
            category=category
        )
        
        self.register_tool(tool)
        self._function_cache[tool_name] = func
        
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
        
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category"""
        return [tool for tool in self.tools.values() if tool.category == category]
        
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return list(self.tools.values())
        
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool with given parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
            
        if not tool.enabled:
            raise ValueError(f"Tool {tool_name} is disabled")
            
        print(colored(f"Executing tool: {tool_name}", "yellow"))
        
        # Get the function
        if tool_name in self._function_cache:
            func = self._function_cache[tool_name]
        else:
            # Import the function dynamically
            module_path, func_name = tool.function.rsplit('.', 1)
            module = __import__(module_path, fromlist=[func_name])
            func = getattr(module, func_name)
            self._function_cache[tool_name] = func
            
        # Validate parameters
        required_params = [p.name for p in tool.parameters if p.required]
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Required parameter '{param}' missing for tool {tool_name}")
                
        # Execute the function
        try:
            result = func(**kwargs)
            print(colored(f"Tool {tool_name} executed successfully", "green"))
            return result
        except Exception as e:
            print(colored(f"Error executing tool {tool_name}: {str(e)}", "red"))
            raise
            
    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get the schema for a tool (useful for LLMs)"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {}
            
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        "default": param.default
                    } for param in tool.parameters
                },
                "required": [p.name for p in tool.parameters if p.required]
            }
        }

# Global registry instance
tool_registry = ToolRegistry()

# Register Alpaca tools
def register_alpaca_tools():
    """Register all Alpaca trading tools"""
    from src.tools import alpaca_tools
    
    # Account tools
    tool_registry.register_function(
        alpaca_tools.get_account,
        category="alpaca_account",
        description="Get Alpaca account information including cash, buying power, and equity"
    )
    
    tool_registry.register_function(
        alpaca_tools.get_positions,
        category="alpaca_portfolio",
        description="Get current positions, optionally filtered by symbols"
    )
    
    tool_registry.register_function(
        alpaca_tools.get_portfolio_history,
        category="alpaca_portfolio",
        description="Get portfolio history with equity and P&L over time"
    )
    
    # Trading tools
    tool_registry.register_function(
        alpaca_tools.place_market_order,
        category="alpaca_trading",
        description="Place a market order to buy or sell stocks"
    )
    
    tool_registry.register_function(
        alpaca_tools.place_limit_order,
        category="alpaca_trading",
        description="Place a limit order with a specific price"
    )
    
    tool_registry.register_function(
        alpaca_tools.get_orders,
        category="alpaca_trading",
        description="Get a list of orders with specified status"
    )
    
    tool_registry.register_function(
        alpaca_tools.cancel_order,
        category="alpaca_trading",
        description="Cancel an order by ID"
    )
    
    # Market data tools
    tool_registry.register_function(
        alpaca_tools.get_bars,
        category="alpaca_market_data",
        description="Get historical price bars for a symbol"
    )
    
    tool_registry.register_function(
        alpaca_tools.get_latest_quote,
        category="alpaca_market_data",
        description="Get the latest quote (bid/ask) for a symbol"
    )
    
    tool_registry.register_function(
        alpaca_tools.get_clock,
        category="alpaca_market_data",
        description="Get current market clock status (open/closed)"
    )
    
    # Portfolio tools for agents
    tool_registry.register_function(
        alpaca_tools.get_portfolio_for_agents,
        category="alpaca_portfolio",
        description="Get Alpaca portfolio data formatted for the agent system"
    )
    
    print(colored(f"Registered {len([t for t in tool_registry.get_all_tools() if t.category.startswith('alpaca')])} Alpaca tools", "green"))