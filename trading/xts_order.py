from utils.pyIB_APIS import IB_APIS
bridge = IB_APIS("http://127.0.0.1:21000")  # Set your bridge URL

def place_order(unique_id, strategy_tag, user_id, exchange, symbol, transaction_type, quantity):
    try:
        # Most args set to defaults for market order
        return bridge.IB_PlaceOrder(
            UniqueID=unique_id,
            StrategyTag=strategy_tag,
            UserID=user_id,
            Exchange=exchange,
            Symbol=symbol,
            TransactionType=transaction_type,
            OrderType="MKT",
            ProductType="NRML",
            Price=0,
            TriggerPrice=0,
            ProfitValue="",
            StoplossValue="",
            Quantity=quantity
        )
    except Exception as e:
        print(f"Order error: {e}")
        return None

def get_order_status(order_id):
    """
    Returns the status of an order (string).
    """
    try:
        return bridge.IB_OrderStatus(order_id)
    except Exception as e:
        print(f"[Order] Error fetching status for OrderID {order_id}: {e}")
        return "UNKNOWN"

def get_filled_qty(order_id):
    """
    Returns the filled (traded) quantity for the order.
    """
    try:
        return int(bridge.IB_OrderFilledQty(order_id))
    except Exception as e:
        print(f"[Order] Error fetching filled qty for OrderID {order_id}: {e}")
        return 0

def square_off_order(order_id):
    """
    Squares off (closes) the given order.
    """
    try:
        bridge.IB_SquareOff(order_id)
        print(f"[Order] Square-off called for OrderID {order_id}")
    except Exception as e:
        print(f"[Order] Error squaring off OrderID {order_id}: {e}")