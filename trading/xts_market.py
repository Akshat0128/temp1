from utils.load_tokken import get_exchange_from_scripmaster
from utils.pyIB_APIS import IB_APIS
import random

bridge = IB_APIS("http://127.0.0.1:7070")
def subscribe_one_token_per_exchange(df):
    """
    At startup, subscribe one random NSEFO and one random BSEFO token from scripmaster.
    """
    nsefo_row = df[df['exchangename'].str.upper().str.contains('NSEFO')].sample(n=1)
    bsefo_row = df[df['exchangename'].str.upper().str.contains('BSEFO')].sample(n=1)

    for row in [nsefo_row, bsefo_row]:
        if not row.empty:
            token = row.iloc[0]['scripname'].strip().upper()
            exchange = get_exchange_from_scripmaster(token)
            try:
                bridge.IB_Subscribe(exchange, token,"MotilalXTS")
                print(f"✅ Subscribed to broker's Feed")
            except Exception as e:
                print(f"❌ Error subscribing broker's Feed")

def get_ltp(symbol):
    exchange = get_exchange_from_scripmaster(symbol)

    try:
        return float(bridge.IB_LTP(exchange, symbol))
    except Exception as e:
        print(f"Error fetching LTP: {e}")
        return 0.0