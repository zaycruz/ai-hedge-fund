import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from termcolor import colored

# Initialize Alpaca clients
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
ALPACA_PAPER = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'

def _get_trading_client() -> TradingClient:
    """Get or create Alpaca trading client."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("Alpaca API credentials not set in environment variables")
    
    return TradingClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY,
        paper=ALPACA_PAPER
    )

def _get_data_client() -> StockHistoricalDataClient:
    """Get or create Alpaca data client."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("Alpaca API credentials not set in environment variables")
    
    return StockHistoricalDataClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY
    )

def get_account() -> Dict[str, Any]:
    """Get Alpaca account information."""
    try:
        print(colored("Getting Alpaca account information...", "cyan"))
        client = _get_trading_client()
        account = client.get_account()
        
        return {
            "id": account.id,
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "portfolio_value": float(account.portfolio_value) if hasattr(account, 'portfolio_value') else float(account.equity),
            "currency": account.currency,
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "account_blocked": account.account_blocked,
            "created_at": str(account.created_at) if account.created_at else None
        }
    except Exception as e:
        print(colored(f"Error fetching account: {str(e)}", "red"))
        return {"error": str(e)}

def get_positions(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get current positions, optionally filtered by symbols."""
    try:
        print(colored("Getting Alpaca positions...", "cyan"))
        client = _get_trading_client()
        positions = client.get_all_positions()
        
        result = []
        for position in positions:
            if symbols is None or position.symbol in symbols:
                result.append({
                    "symbol": position.symbol,
                    "qty": float(position.qty),
                    "side": position.side,
                    "market_value": float(position.market_value),
                    "avg_entry_price": float(position.avg_entry_price),
                    "current_price": float(position.current_price) if hasattr(position, 'current_price') else None,
                    "unrealized_pl": float(position.unrealized_pl) if hasattr(position, 'unrealized_pl') else None,
                    "unrealized_plpc": float(position.unrealized_plpc) if hasattr(position, 'unrealized_plpc') else None,
                    "cost_basis": float(position.cost_basis) if hasattr(position, 'cost_basis') else float(position.avg_entry_price) * float(position.qty),
                    "asset_id": position.asset_id
                })
        
        return result
    except Exception as e:
        print(colored(f"Error fetching positions: {str(e)}", "red"))
        return []

def get_portfolio_history(period: str = "1M", timeframe: str = "1D") -> Dict[str, Any]:
    """Get portfolio history."""
    try:
        print(colored(f"Getting portfolio history for period {period} with {timeframe} timeframe...", "cyan"))
        client = _get_trading_client()
        history = client.get_portfolio_history(period=period, timeframe=timeframe)
        
        return {
            "timestamp": [str(ts) for ts in history.timestamp] if history.timestamp else [],
            "equity": list(history.equity) if history.equity else [],
            "profit_loss": list(history.profit_loss) if history.profit_loss else [],
            "profit_loss_pct": list(history.profit_loss_pct) if history.profit_loss_pct else [],
            "base_value": history.base_value if hasattr(history, 'base_value') else None,
            "timeframe": history.timeframe if hasattr(history, 'timeframe') else timeframe
        }
    except Exception as e:
        print(colored(f"Error getting portfolio history: {str(e)}", "red"))
        return {"error": str(e)}

def place_market_order(symbol: str, qty: float, side: str = "buy") -> Dict[str, Any]:
    """Place a market order."""
    try:
        print(colored(f"Placing {side} market order for {qty} shares of {symbol}...", "cyan"))
        client = _get_trading_client()
        
        # Create market order request
        market_order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit order
        order = client.submit_order(market_order_data)
        
        return {
            "id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side,
            "status": order.status,
            "created_at": str(order.created_at) if order.created_at else None,
            "type": order.order_type if hasattr(order, 'order_type') else "market"
        }
    except Exception as e:
        print(colored(f"Error placing order: {str(e)}", "red"))
        return {"error": str(e)}

def place_limit_order(symbol: str, qty: float, limit_price: float, side: str = "buy") -> Dict[str, Any]:
    """Place a limit order."""
    try:
        print(colored(f"Placing {side} limit order for {qty} shares of {symbol} at {limit_price}...", "cyan"))
        client = _get_trading_client()
        
        # Create limit order request
        limit_order_data = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit order
        order = client.submit_order(limit_order_data)
        
        return {
            "id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side,
            "status": order.status,
            "limit_price": float(order.limit_price) if hasattr(order, 'limit_price') else limit_price,
            "created_at": str(order.created_at) if order.created_at else None,
            "type": order.order_type if hasattr(order, 'order_type') else "limit"
        }
    except Exception as e:
        print(colored(f"Error placing limit order: {str(e)}", "red"))
        return {"error": str(e)}

def get_orders(status: str = "open", limit: int = 50) -> List[Dict[str, Any]]:
    """Get a list of orders."""
    try:
        print(colored(f"Getting {status} orders...", "cyan"))
        client = _get_trading_client()
        
        # Map status string to enum
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL
        }
        
        # Create get orders request
        request_params = GetOrdersRequest(
            status=status_map.get(status.lower(), QueryOrderStatus.OPEN),
            limit=limit
        )
        
        # Get orders
        orders = client.get_orders(request_params)
        
        result = []
        for order in orders:
            order_dict = {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "status": order.status,
                "created_at": str(order.created_at) if order.created_at else None,
                "type": order.order_type if hasattr(order, 'order_type') else None
            }
            
            # Add optional fields if present
            if hasattr(order, 'limit_price') and order.limit_price:
                order_dict["limit_price"] = float(order.limit_price)
            if hasattr(order, 'stop_price') and order.stop_price:
                order_dict["stop_price"] = float(order.stop_price)
                
            result.append(order_dict)
            
        return result
    except Exception as e:
        print(colored(f"Error getting orders: {str(e)}", "red"))
        return []

def cancel_order(order_id: str) -> Dict[str, Any]:
    """Cancel an order by ID."""
    try:
        print(colored(f"Canceling order {order_id}...", "cyan"))
        client = _get_trading_client()
        client.cancel_order(order_id)
        return {"status": "success", "message": f"Order {order_id} cancelled"}
    except Exception as e:
        print(colored(f"Error canceling order: {str(e)}", "red"))
        return {"error": str(e)}

def get_bars(symbol: str, start_date: str, end_date: str, timeframe: str = "1Day") -> List[Dict[str, Any]]:
    """Get historical bars for a symbol."""
    try:
        print(colored(f"Getting {timeframe} bars for {symbol}...", "cyan"))
        client = _get_data_client()
        
        # Map timeframe strings to TimeFrame objects
        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day
        }
        
        tf = timeframe_map.get(timeframe, TimeFrame.Day)
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Create request
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end
        )
        
        # Get bars
        bars_data = client.get_stock_bars(request_params)
        
        result = []
        if symbol in bars_data:
            for bar in bars_data[symbol]:
                result.append({
                    "timestamp": str(bar.timestamp),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume)
                })
                
        return result
    except Exception as e:
        print(colored(f"Error getting bars: {str(e)}", "red"))
        return []

def get_latest_quote(symbol: str) -> Dict[str, Any]:
    """Get the latest quote for a symbol."""
    try:
        print(colored(f"Getting latest quote for {symbol}...", "cyan"))
        client = _get_data_client()
        
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = client.get_stock_latest_quote(request_params)
        
        if symbol in quotes:
            quote = quotes[symbol]
            return {
                "symbol": symbol,
                "ask_price": float(quote.ask_price) if quote.ask_price else None,
                "ask_size": int(quote.ask_size) if quote.ask_size else None,
                "bid_price": float(quote.bid_price) if quote.bid_price else None,
                "bid_size": int(quote.bid_size) if quote.bid_size else None,
                "timestamp": str(quote.timestamp) if quote.timestamp else None
            }
        else:
            return {"symbol": symbol, "error": "No quote data available"}
    except Exception as e:
        print(colored(f"Error getting quote: {str(e)}", "red"))
        return {"error": str(e)}

def get_clock() -> Dict[str, Any]:
    """Get the current market clock."""
    try:
        print(colored("Getting market clock...", "cyan"))
        client = _get_trading_client()
        clock = client.get_clock()
        
        return {
            "timestamp": str(clock.timestamp),
            "is_open": clock.is_open,
            "next_open": str(clock.next_open),
            "next_close": str(clock.next_close)
        }
    except Exception as e:
        print(colored(f"Error getting market clock: {str(e)}", "red"))
        return {"error": str(e)}

# Helper function to get portfolio data in a format compatible with the existing portfolio structure
def get_portfolio_for_agents(tickers: List[str]) -> Dict[str, Any]:
    """Get Alpaca portfolio data formatted for the agent system."""
    try:
        account = get_account()
        positions = get_positions(tickers)
        
        if "error" in account:
            return {}
        
        # Initialize portfolio structure
        portfolio = {
            "cash": account["cash"],
            "buying_power": account["buying_power"],
            "portfolio_value": account["portfolio_value"],
            "positions": {},
            "realized_gains": {}
        }
        
        # Initialize positions for all tickers
        for ticker in tickers:
            portfolio["positions"][ticker] = {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0
            }
            portfolio["realized_gains"][ticker] = {
                "long": 0.0,
                "short": 0.0
            }
        
        # Update with actual positions
        for position in positions:
            ticker = position["symbol"]
            if ticker in portfolio["positions"]:
                if position["side"] == "long":
                    portfolio["positions"][ticker]["long"] = int(position["qty"])
                    portfolio["positions"][ticker]["long_cost_basis"] = position["cost_basis"] / position["qty"] if position["qty"] > 0 else 0
                elif position["side"] == "short":
                    portfolio["positions"][ticker]["short"] = int(position["qty"])
                    portfolio["positions"][ticker]["short_cost_basis"] = position["cost_basis"] / position["qty"] if position["qty"] > 0 else 0
                    portfolio["positions"][ticker]["short_margin_used"] = position["market_value"]
        
        return portfolio
        
    except Exception as e:
        print(colored(f"Error getting portfolio for agents: {str(e)}", "red"))
        return {}