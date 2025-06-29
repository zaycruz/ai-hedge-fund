from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from termcolor import colored
from langchain.tools import Tool as LangChainTool
from src.tools.tool_registry import tool_registry
from src.llm.models import get_model, ModelProvider
import json

class BaseAgent(ABC):
    """Base class for all agents with tool support"""
    
    def __init__(self, name: str, model: str = "gpt-4o", tools: Optional[List[str]] = None):
        self.name = name
        self.model = model
        self.tool_names = tools or []
        # Default to OpenAI provider if model is a standard OpenAI model
        if model.startswith("gpt"):
            self.llm = get_model(model, ModelProvider.OPENAI)
        else:
            # For other models, would need provider information
            self.llm = get_model(model, ModelProvider.OPENAI)
        
        if self.llm is None:
            raise ValueError(f"Failed to initialize LLM for model {model}")
        print(colored(f"Initializing {name} agent with {len(self.tool_names)} tools", "cyan"))
        
    @abstractmethod
    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the current state and provide recommendations"""
        pass
        
    def get_available_tools(self) -> List[LangChainTool]:
        """Get LangChain tools for this agent"""
        langchain_tools = []
        
        for tool_name in self.tool_names:
            tool = tool_registry.get_tool(tool_name)
            if tool and tool.enabled:
                # Create a LangChain tool wrapper
                def create_tool_func(t_name):
                    def tool_func(**kwargs):
                        return tool_registry.execute_tool(t_name, **kwargs)
                    return tool_func
                    
                lc_tool = LangChainTool(
                    name=tool_name,
                    description=tool.description,
                    func=create_tool_func(tool_name)
                )
                langchain_tools.append(lc_tool)
                
        return langchain_tools
        
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool if available to this agent"""
        if tool_name not in self.tool_names:
            raise ValueError(f"Tool {tool_name} not available to {self.name}")
            
        return tool_registry.execute_tool(tool_name, **kwargs)
        
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools available to this agent"""
        schemas = []
        for tool_name in self.tool_names:
            schema = tool_registry.get_tool_schema(tool_name)
            if schema:
                schemas.append(schema)
        return schemas
        
    def format_tools_for_prompt(self) -> str:
        """Format available tools for inclusion in prompts"""
        if not self.tool_names:
            return "No tools available."
            
        tool_descriptions = []
        for tool_name in self.tool_names:
            tool = tool_registry.get_tool(tool_name)
            if tool:
                params = [f"{p.name}: {p.type}" for p in tool.parameters]
                tool_descriptions.append(
                    f"- {tool.name}({', '.join(params)}): {tool.description}"
                )
                
        return "Available tools:\n" + "\n".join(tool_descriptions)

class ToolAgent(BaseAgent):
    """A generic agent that can use any configured tools"""
    
    def __init__(self, name: str, description: str, model: str = "gpt-4o", 
                 tools: Optional[List[str]] = None, system_prompt: Optional[str] = None):
        super().__init__(name, model, tools)
        self.description = description
        self.system_prompt = system_prompt or f"You are {name}, {description}"
        
    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using configured tools and system prompt"""
        print(colored(f"\n{self.name} analyzing with tools...", "cyan"))
        
        # Get market data
        market_data = state.get("market_data", {})
        news_summary = state.get("news_summary", "")
        portfolio = state.get("portfolio", {})
        
        # Build the prompt
        tools_info = self.format_tools_for_prompt()
        
        prompt = f"""
{self.system_prompt}

{tools_info}

Current market data:
{json.dumps(market_data, indent=2)}

News summary:
{news_summary}

Current portfolio:
{json.dumps(portfolio, indent=2)}

Based on this information and using your available tools, provide your analysis and recommendations.
Format your response as JSON with the following structure:
{{
    "recommendation": "BUY/SELL/HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "Your detailed reasoning",
    "suggested_allocation": 0.0-1.0,
    "tool_results": {{}}  // Results from any tools you used
}}
"""
        
        try:
            # If tools are available, use them through LangChain
            if self.tool_names:
                # Here you would integrate with LangChain agents to use tools
                # For now, we'll use direct tool execution as an example
                tool_results = {}
                
                # Example: Use get_account tool if available
                if "get_account" in self.tool_names:
                    try:
                        account_info = self.execute_tool("get_account")
                        tool_results["account_info"] = account_info
                    except Exception as e:
                        print(colored(f"Error using get_account tool: {e}", "red"))
                        
                # Include tool results in the prompt
                if tool_results:
                    prompt += f"\n\nTool execution results:\n{json.dumps(tool_results, indent=2)}"
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            
            # Parse response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
                
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "recommendation": "HOLD",
                    "confidence": 0.5,
                    "reasoning": response_text,
                    "suggested_allocation": 0.0
                }
                
            return {
                "agent": self.name,
                "description": self.description,
                **result
            }
            
        except Exception as e:
            print(colored(f"Error in {self.name} analysis: {e}", "red"))
            return {
                "agent": self.name,
                "description": self.description,
                "recommendation": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error during analysis: {str(e)}",
                "suggested_allocation": 0.0
            }