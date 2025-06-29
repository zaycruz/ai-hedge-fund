import json
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from termcolor import colored

from src.graph.state import AgentState, show_agent_reasoning
from src.agents.base_agent import BaseAgent
from src.tools.tool_registry import tool_registry
from src.utils.progress import progress
from src.llm.models import get_model, ModelProvider
from pydantic import BaseModel, Field
from typing_extensions import Literal


class PortfolioDecision(BaseModel):
    action: Literal["buy", "sell", "short", "cover", "hold"]
    quantity: int = Field(description="Number of shares to trade")
    confidence: float = Field(description="Confidence in the decision, between 0.0 and 100.0")
    reasoning: str = Field(description="Reasoning for the decision")


class PortfolioManagerOutput(BaseModel):
    decisions: dict[str, PortfolioDecision] = Field(description="Dictionary of ticker to trading decisions")


class ToolEnabledPortfolioManager(BaseAgent):
    """Portfolio Manager with tool support"""
    
    def __init__(self, tools: Optional[List[str]] = None):
        # Default tools for portfolio manager
        default_tools = [
            "get_account",
            "get_positions", 
            "get_portfolio_history",
            "get_latest_quote",
            "get_clock"
        ]
        
        # Combine default tools with any additional tools
        all_tools = list(set(default_tools + (tools or [])))
        
        super().__init__(
            name="Tool-Enabled Portfolio Manager",
            model="gpt-4o",
            tools=all_tools
        )
        
        print(colored(f"Portfolio Manager initialized with {len(self.tool_names)} tools", "cyan"))
        
    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Portfolio manager's main analysis method"""
        # This is used for the base agent interface
        # The actual portfolio management logic is in the function below
        return self.make_portfolio_decisions(state)
        
    def make_portfolio_decisions(self, state: AgentState) -> Dict[str, Any]:
        """Makes final trading decisions and generates orders for multiple tickers"""
        
        # Get the portfolio and analyst signals
        portfolio = state["data"]["portfolio"]
        analyst_signals = state["data"]["analyst_signals"]
        tickers = state["data"]["tickers"]
        
        # Use tools to get real-time data
        tool_data = {}
        
        # Get account information
        if "get_account" in self.tool_names:
            try:
                account_info = self.execute_tool("get_account")
                tool_data["account"] = account_info
                print(colored(f"Account cash: ${account_info.get('cash', 0):,.2f}", "green"))
                print(colored(f"Buying power: ${account_info.get('buying_power', 0):,.2f}", "green"))
            except Exception as e:
                print(colored(f"Error getting account info: {e}", "red"))
                
        # Get current positions
        if "get_positions" in self.tool_names:
            try:
                positions = self.execute_tool("get_positions", symbols=tickers)
                tool_data["positions"] = positions
                print(colored(f"Found {len(positions)} positions", "green"))
            except Exception as e:
                print(colored(f"Error getting positions: {e}", "red"))
                
        # Get latest quotes for tickers
        if "get_latest_quote" in self.tool_names:
            quotes = {}
            for ticker in tickers:
                try:
                    quote = self.execute_tool("get_latest_quote", symbol=ticker)
                    quotes[ticker] = quote
                except Exception as e:
                    print(colored(f"Error getting quote for {ticker}: {e}", "red"))
            tool_data["quotes"] = quotes
            
        # Get market clock
        if "get_clock" in self.tool_names:
            try:
                clock = self.execute_tool("get_clock")
                tool_data["market_clock"] = clock
                print(colored(f"Market is {'OPEN' if clock.get('is_open') else 'CLOSED'}", "yellow"))
            except Exception as e:
                print(colored(f"Error getting market clock: {e}", "red"))
        
        # Get position limits, current prices, and signals for every ticker
        position_limits = {}
        current_prices = {}
        max_shares = {}
        signals_by_ticker = {}
        
        for ticker in tickers:
            progress.update_status("portfolio_manager", ticker, "Processing analyst signals")
            
            # Get position limits and current prices for the ticker
            risk_data = analyst_signals.get("risk_management_agent", {}).get(ticker, {})
            position_limits[ticker] = risk_data.get("remaining_position_limit", 0)
            
            # Use real-time quote if available, otherwise use risk data
            if ticker in tool_data.get("quotes", {}):
                quote = tool_data["quotes"][ticker]
                current_prices[ticker] = (quote.get("bid_price", 0) + quote.get("ask_price", 0)) / 2
            else:
                current_prices[ticker] = risk_data.get("current_price", 0)
            
            # Calculate maximum shares allowed based on position limit and price
            if current_prices[ticker] > 0:
                max_shares[ticker] = int(position_limits[ticker] / current_prices[ticker])
            else:
                max_shares[ticker] = 0
            
            # Get signals for the ticker
            ticker_signals = {}
            for agent, signals in analyst_signals.items():
                if agent != "risk_management_agent" and ticker in signals:
                    ticker_signals[agent] = {
                        "signal": signals[ticker]["signal"], 
                        "confidence": signals[ticker]["confidence"]
                    }
            signals_by_ticker[ticker] = ticker_signals
            
        progress.update_status("portfolio_manager", None, "Generating trading decisions")
        
        # Generate the trading decision
        result = self._generate_trading_decision(
            tickers=tickers,
            signals_by_ticker=signals_by_ticker,
            current_prices=current_prices,
            max_shares=max_shares,
            portfolio=portfolio,
            tool_data=tool_data,
            state=state,
        )
        
        # Create the portfolio management message
        message = HumanMessage(
            content=json.dumps({ticker: decision.model_dump() for ticker, decision in result.decisions.items()}),
            name="portfolio_manager",
        )
        
        # Print the decision if the flag is set
        if state["metadata"]["show_reasoning"]:
            show_agent_reasoning({ticker: decision.model_dump() for ticker, decision in result.decisions.items()}, "Portfolio Manager")
            
        progress.update_status("portfolio_manager", None, "Done")
        
        return {
            "messages": state["messages"] + [message],
            "data": state["data"],
        }
        
    def _generate_trading_decision(
        self,
        tickers: list[str],
        signals_by_ticker: dict[str, dict],
        current_prices: dict[str, float],
        max_shares: dict[str, int],
        portfolio: dict[str, float],
        tool_data: dict[str, Any],
        state: AgentState,
    ) -> PortfolioManagerOutput:
        """Generates trading decisions with tool data"""
        
        # Create the prompt template
        template = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a portfolio manager making final trading decisions based on multiple tickers.
                
                You have access to real-time data through tools:
                - Account information (cash, buying power, etc.)
                - Current positions
                - Real-time quotes
                - Market status
                
                Trading Rules:
                - For long positions:
                  * Only buy if you have available cash
                  * Only sell if you currently hold long shares of that ticker
                  * Sell quantity must be ≤ current long position shares
                  * Buy quantity must be ≤ max_shares for that ticker
                
                - For short positions:
                  * Only short if you have available margin (position value × margin requirement)
                  * Only cover if you currently have short shares of that ticker
                  * Cover quantity must be ≤ current short position shares
                  * Short quantity must respect margin requirements
                
                - The max_shares values are pre-calculated to respect position limits
                - Consider both long and short opportunities based on signals
                - Maintain appropriate risk management with both long and short exposure
                - Consider market hours when making decisions
                
                Available Actions:
                - "buy": Open or add to long position
                - "sell": Close or reduce long position
                - "short": Open or add to short position
                - "cover": Close or reduce short position
                - "hold": No action
                """,
            ),
            (
                "human",
                """Based on the team's analysis and real-time data, make your trading decisions for each ticker.
                
                Here are the signals by ticker:
                {signals_by_ticker}
                
                Current Prices:
                {current_prices}
                
                Maximum Shares Allowed For Purchases:
                {max_shares}
                
                Portfolio Cash: {portfolio_cash}
                Current Positions: {portfolio_positions}
                Current Margin Requirement: {margin_requirement}
                Total Margin Used: {total_margin_used}
                
                Real-Time Tool Data:
                {tool_data}
                
                Output strictly in JSON with the following structure:
                {{
                  "decisions": {{
                    "TICKER1": {{
                      "action": "buy/sell/short/cover/hold",
                      "quantity": integer,
                      "confidence": float between 0 and 100,
                      "reasoning": "string"
                    }},
                    "TICKER2": {{
                      ...
                    }},
                    ...
                  }}
                }}
                """,
            ),
        ])
        
        # Generate the prompt
        prompt = template.invoke({
            "signals_by_ticker": json.dumps(signals_by_ticker, indent=2),
            "current_prices": json.dumps(current_prices, indent=2),
            "max_shares": json.dumps(max_shares, indent=2),
            "portfolio_cash": f"{portfolio.get('cash', 0):.2f}",
            "portfolio_positions": json.dumps(portfolio.get("positions", {}), indent=2),
            "margin_requirement": f"{portfolio.get('margin_requirement', 0):.2f}",
            "total_margin_used": f"{portfolio.get('margin_used', 0):.2f}",
            "tool_data": json.dumps(tool_data, indent=2),
        })
        
        # Get response from LLM
        try:
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
                result_data = json.loads(json_match.group())
                
                # Convert to PortfolioManagerOutput
                decisions = {}
                for ticker, decision_data in result_data.get("decisions", {}).items():
                    decisions[ticker] = PortfolioDecision(**decision_data)
                    
                return PortfolioManagerOutput(decisions=decisions)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(colored(f"Error generating trading decision: {e}", "red"))
            # Return default hold decisions
            decisions = {
                ticker: PortfolioDecision(
                    action="hold",
                    quantity=0,
                    confidence=0.0,
                    reasoning=f"Error in decision generation: {str(e)}"
                )
                for ticker in tickers
            }
            return PortfolioManagerOutput(decisions=decisions)


# Function to use in the existing graph system
def portfolio_management_agent_with_tools(state: AgentState):
    """Portfolio management agent function with tool support"""
    manager = ToolEnabledPortfolioManager()
    return manager.make_portfolio_decisions(state)