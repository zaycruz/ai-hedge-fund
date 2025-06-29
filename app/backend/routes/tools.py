from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from termcolor import colored

# Import tool registry from src
import sys
sys.path.append("/workspace")
from src.tools.tool_registry import tool_registry, register_alpaca_tools, Tool, ToolParameter
from src.agents.base_agent import ToolAgent

router = APIRouter(prefix="/api/tools", tags=["tools"])

# Initialize Alpaca tools on startup
try:
    register_alpaca_tools()
    print(colored("Alpaca tools registered successfully", "green"))
except Exception as e:
    print(colored(f"Error registering Alpaca tools: {e}", "red"))

class ToolInfo(BaseModel):
    """Tool information for API responses"""
    name: str
    description: str
    category: str
    parameters: List[Dict[str, Any]]
    enabled: bool

class ExecuteToolRequest(BaseModel):
    """Request to execute a tool"""
    tool_name: str
    parameters: Dict[str, Any]

class CustomAgentRequest(BaseModel):
    """Request to create a custom agent"""
    name: str
    description: str
    model: str = "gpt-4o"
    tools: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None

class AgentAnalysisRequest(BaseModel):
    """Request for agent analysis"""
    agent_name: str
    market_data: Dict[str, Any] = Field(default_factory=dict)
    news_summary: str = ""
    portfolio: Dict[str, Any] = Field(default_factory=dict)

# Store custom agents in memory (in production, use a database)
custom_agents: Dict[str, ToolAgent] = {}

@router.get("/", response_model=List[ToolInfo])
async def get_all_tools():
    """Get all available tools"""
    try:
        tools = tool_registry.get_all_tools()
        return [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                category=tool.category,
                parameters=[{
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                } for p in tool.parameters],
                enabled=tool.enabled
            )
            for tool in tools
        ]
    except Exception as e:
        print(colored(f"Error getting tools: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories", response_model=Dict[str, List[ToolInfo]])
async def get_tools_by_category():
    """Get tools grouped by category"""
    try:
        tools = tool_registry.get_all_tools()
        categories = {}
        
        for tool in tools:
            if tool.category not in categories:
                categories[tool.category] = []
            
            categories[tool.category].append(
                ToolInfo(
                    name=tool.name,
                    description=tool.description,
                    category=tool.category,
                    parameters=[{
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default
                    } for p in tool.parameters],
                    enabled=tool.enabled
                )
            )
        
        return categories
    except Exception as e:
        print(colored(f"Error getting tools by category: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_tool(request: ExecuteToolRequest):
    """Execute a tool with given parameters"""
    try:
        result = tool_registry.execute_tool(
            request.tool_name,
            **request.parameters
        )
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(colored(f"Error executing tool: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema/{tool_name}")
async def get_tool_schema(tool_name: str):
    """Get schema for a specific tool"""
    try:
        schema = tool_registry.get_tool_schema(tool_name)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        return schema
    except Exception as e:
        print(colored(f"Error getting tool schema: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents")
async def create_custom_agent(request: CustomAgentRequest):
    """Create a custom agent with tools"""
    try:
        # Validate tools exist
        for tool_name in request.tools:
            if not tool_registry.get_tool(tool_name):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Tool {tool_name} not found"
                )
        
        # Create the agent
        agent = ToolAgent(
            name=request.name,
            description=request.description,
            model=request.model,
            tools=request.tools,
            system_prompt=request.system_prompt
        )
        
        # Store the agent
        custom_agents[request.name] = agent
        
        return {
            "success": True,
            "agent": {
                "name": request.name,
                "description": request.description,
                "model": request.model,
                "tools": request.tools
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(colored(f"Error creating custom agent: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents", response_model=List[Dict[str, Any]])
async def get_custom_agents():
    """Get all custom agents"""
    return [
        {
            "name": agent.name,
            "description": agent.description,
            "model": agent.model,
            "tools": agent.tool_names
        }
        for agent in custom_agents.values()
    ]

@router.post("/agents/{agent_name}/analyze")
async def analyze_with_agent(agent_name: str, request: AgentAnalysisRequest):
    """Run analysis with a custom agent"""
    try:
        agent = custom_agents.get(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        # Create state for analysis
        state = {
            "market_data": request.market_data,
            "news_summary": request.news_summary,
            "portfolio": request.portfolio
        }
        
        # Run analysis
        result = agent.analyze(state)
        
        return {
            "success": True,
            "analysis": result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(colored(f"Error running agent analysis: {e}", "red"))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/agents/{agent_name}")
async def delete_custom_agent(agent_name: str):
    """Delete a custom agent"""
    if agent_name not in custom_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    del custom_agents[agent_name]
    return {"success": True, "message": f"Agent {agent_name} deleted"}