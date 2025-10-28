from utils.pyIB_APIS import IB_APIS
bridge = IB_APIS("http://127.0.0.1:21000") # Set your bridge URL

def place_order(unique_id, strategy_tag, user_id, exchange, symbol, transaction_type, quantity):
    try:
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

def get_order_status(request_id): # Parameter can be RequestID or OrderID based on bridge API
    """
    Returns the status of an order (string) using RequestID or OrderID.
    """
    try:
        # Assuming IB_OrderStatus accepts RequestID based on typical bridge behavior
        return bridge.IB_OrderStatus(request_id)
    except Exception as e:
        print(f"[Order] Error fetching status for ID {request_id}: {e}")
        return "UNKNOWN"

def get_filled_qty(request_id_or_order_id): # Parameter can be RequestID or OrderID
    """
    Returns the filled (traded) quantity for the order using RequestID or OrderID.
    """
    try:
        # IB_OrderFilledQty might accept RequestID or broker's OrderID
        # Let's assume it works with the RequestID returned by place_order functions
        filled_qty = bridge.IB_OrderFilledQty(request_id_or_order_id)
        # Handle potential None or non-integer return values gracefully
        return int(filled_qty) if filled_qty is not None else 0
    except Exception as e:
        print(f"[Order] Error fetching filled qty for ID {request_id_or_order_id}: {e}")
        return 0

# Corrected square_off_order function
def square_off_order(request_id):
    """
    Cancels or Exits the specific order associated with the given RequestID[cite: 251].
    Uses IB_CancelOrExitOrder as per documentation.
    """
    try:
        # Use IB_CancelOrExitOrder with the RequestID from placing the order [cite: 251, 253]
        success = bridge.IB_CancelOrExitOrder(request_id)
        if success:
            print(f"[Order] Cancel/Exit called successfully for RequestID {request_id}")
        else:
            # IB_CancelOrExitOrder returns bool[cite: 260], False might mean request accepted but failed later, or immediate failure.
            # Check bridge logs for details if needed.
            print(f"[Order] Cancel/Exit call for RequestID {request_id} returned False or failed.")
    except Exception as e:
        # Log exceptions during the API call itself
        print(f"[Order] Error calling Cancel/Exit for RequestID {request_id}: {e}")