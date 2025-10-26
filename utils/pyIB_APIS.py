import requests
from requests.exceptions import HTTPError

class IB_APIS:
    source_url = ""
    timeout    = 0

    # Response code
    OK_STATUS          = 200 #OK means Success
    '''
    CREATED_SUCEES     = 201 #Created means Success
    NO_CONTENT_SUCESS  = 204 #No Content means Success
    REDIRECT           = 304 #Unchanged means Redirect
    BAD_REQUEST        = 400 #Bad Request means Failure
    UNAUTH_FAILURE     = 401 #Unauthorized means Failure
    FORBIDDEN_FAILURE  = 403 #Forbidden means Failure
    NOT_FOUND          = 404 #Not Found means Failure
    NOT_ALLOWED        = 405 #Method Not Allowed means Failure
    GONE_FAILURE       = 410 #Gone means Failure
    INTERNAL_SERV_ERROR = 500 #Internal Server Error means Failure
    '''

    def __init__(self, source_url, timeout=0):
        self.source_url = source_url
        self.timeout    = timeout

    def _Check_Status(self, response):
        if ("status" not in response.text):
            raise ValueError("LOG_ERROR::  "+response.text)

        if (response.ok):
            response = response.json()
            # print(response)
            if(response['status'] == 'error'):
                print("LOG_RESPONSE_ERROR::  "+response['error'])
                return False
            else:
                # print("Success!")
                return True
        else:
            raise ValueError("LOG_ERROR_CODE::  Getting Error code:"+ response.status_code)
        
    def IB_Ping(self):
        '''
        Description: Used to check the status of the Bridge.

            Return Type: boolean

            If True, mean IAB is running and  Trading also started, Otherwise IAB is not started or some issue exists in connectivity or Trading is stopped

        '''
        url = self.source_url + "/Ping"
        try:
            response = requests.get(url)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_SquareOff(self, UserID:str):
        '''
        Description: Square Off all the positions of provided User ID. It will square off all the positions including positions taken manually (if any) and further trading will be stopped for the session. 

            Imp Note
            It square off Intraday CNC and NRML Positions as per the General Settings in IAB.
            Further trading will be stopped in the User for the session or untill bridge restarts.

            Parameter: UserID (mandatory)- User ID of the user you wish to perform squareoff
            If User ID is supplied as null or empty string, the Bridge will initiate Square Off for the first active logged-in user.

            If the User ID is supplied as ALL, then it will Square off all logged-in users.

            Return Type: bool
        '''
        if(isinstance(UserID, str) == False):
            print("Please Enter UserID as string!")
            return
        
        url = self.source_url + "/SquareOff"
        data = {'UserId': UserID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO::  Host Server Not Reachable")

    def IB_SquareOffAll(self):
        '''
        Description: Square Off all the positions from all active logged-in users. It will square off all the positions including positions taken manually (if any) and further trading will be stopped for the session for all active users in the bridge. 

            Imp Note
            It square off Intraday CNC and NRML Positions as per the General Settings in IAB.
            Further trading will be stopped in all Users for the session or untill bridge restarts.

            Return Type: bool
        '''
        url = self.source_url + "/SquareOffAll"
        try:
            response = requests.post(url)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO::  Host Server Not Reachable")
    
    def IB_SquareOffStrategy(self, StrategyTag:str):
        '''
        Description: Square Off / Exit all the Orders related to the provided Strategy ID.

            Imp Note
            It Exits the Intraday CNC and NRML Positions.
            Further trading will be stopped for the Strategy until bridge restarts.
            It will Exit all orders under the strategy from all the related users.

            Parameter: StrategyTag(mandatory)- Strategy ID for which you wish to perform squareoff. Providing a valid Strategy Tag is mandatory.

            Return Type: bool
        '''
        if(isinstance(StrategyTag, str) == False):
            print("Please Enter StrategyTag as string!")
            return
        
        url = self.source_url + "/SquareOffStrategy"
        data = {'StrategyTag': StrategyTag }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_MTM(self, UserID:str):
        '''
        Description: Function to get the MTM of provided userid. It provides complete MTM including any manual positions as well.

            Parameter: UserID - User ID of the user you wish to check MTM.
            If UserID supplied as null or empty string, then Bridge will return the MTM for the first active logged-in user.

            Return Type: bool
        '''
        if(isinstance(UserID, str) == False):
            print("Please Enter UserID as string!")
            return
        
        url = self.source_url + "/MTM"
        data = {'UserID': UserID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_AvailableMargin(self, UserID:str):
        '''
        Description: Function to get the Available Margin in the mentioned account. This is generally Equity Margin available or ALL margin depending upon the broker.

            Parameter: UserID - User ID of the user you wish to check MTM.
            If User ID supplied as null or empty string, then Bridge will return the Margin for the first active logged-in user.

            If the User ID is supplied as ALL, then it will add Margins of all logged-in users and provide the same.

            Return Type: Decimal
        '''
        if(isinstance(UserID, str) == False):
            print("Please Enter UserID as string!")
            return
        
        url = self.source_url + "/AvailableMargin"
        data = {'UserID': UserID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO::  Host Server Not Reachable")

    def IB_AvailableMarginCommodity(self, UserID:str):
        '''
        Description: Function to get the Available Margin for commodity segment for the mentioned account.

            Parameter: UserID - User ID of the user you wish to check MTM.
            If User ID supplied as null or empty string, then Bridge will return the Margin for the first active logged-in user.

            If the User ID is supplied as ALL, then it will add Margins of all logged-in users and provide the same.

            Return Type: Decimal

        '''
        if(isinstance(UserID, str) == False):
            print("Please Enter UserID as string!")
            return
        
        url = self.source_url + "/AvailableMarginCommodity"
        data = {'UserID': UserID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO::  Host Server Not Reachable")
			
	# Mapped Order Placement Methods Implemetation
    def IB_MappedOrderSch(self, SignalID:int, 
                            StrategyTag:str,
                            SourceSymbol:str, 
                            TransactionType:str, 
                            OrderType:str, 
                            ProductType:str, 
                            Price:float, 
                            TriggerPrice:float, 
							Quantity:int, 
                            ProfitValue:str, 
                            StoplossValue:str,
							SLTrailingValue:str="", 
                            SignalLTP:float=0,
                            OptionsType:str="", 
                            ScheduleTime:str=""):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Exit the order by providing as signal id. Order can be exited without providing Signal ID as well in that case order will be exited in FIFO.
        '''
        url = self.source_url + "/MappedOrderSch"
        data = {'SignalID': SignalID, 
                'StrategyTag':StrategyTag,                 
                'SourceSymbol':SourceSymbol, 
                'TransactionType':TransactionType, 
                'OrderType':OrderType,  
                'ProductType':ProductType, 
				'Price':Price, 
				'TriggerPrice':TriggerPrice, 
                'Quantity':Quantity, 
                'Target':ProfitValue, 
                'StopLoss':StoplossValue, 
                'TrailingStoploss':SLTrailingValue, 
                'SignalLTP':SignalLTP, 
                'OptionsType':OptionsType, 
                'ScheduleTime': ScheduleTime }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
			
    def IB_MappedOrderAdv(self, SignalID:int, 
                            StrategyTag:str,
                            SourceSymbol:str, 
                            TransactionType:str, 
                            OrderType:str, 
                            ProductType:str, 
                            Price:float, 
                            TriggerPrice:float, 
							Quantity:int, 
                            ProfitValue:str, 
                            StoplossValue:str,
							SLTrailingValue:str="", 
                            SignalLTP:float=0,
                            OptionsType:str=""):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Exit the order by providing as signal id. Order can be exited without providing Signal ID as well in that case order will be exited in FIFO.
        '''
        url = self.source_url + "/MappedOrderAdv"
        data = {'SignalID': SignalID, 
                'StrategyTag':StrategyTag,                 
                'SourceSymbol':SourceSymbol, 
                'TransactionType':TransactionType, 
                'OrderType':OrderType,  
                'ProductType':ProductType, 
				'Price':Price, 
				'TriggerPrice':TriggerPrice, 
                'Quantity':Quantity, 
                'Target':ProfitValue, 
                'StopLoss':StoplossValue, 
                'TrailingStoploss':SLTrailingValue, 
                'SignalLTP':SignalLTP, 
                'OptionsType':OptionsType }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
	
    def IB_MappedOrderMod(self, SignalID:int, 
                            StrategyTag:str,
                            SourceSymbol:str, 
                            TransactionType:str, 
                            OrderType:str, 
                            Price:float, 
                            TriggerPrice:float, 
							Quantity:int, 
                            SignalLTP:float=0):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Exit the order by providing as signal id. Order can be exited without providing Signal ID as well in that case order will be exited in FIFO.
        '''
        url = self.source_url + "/MappedOrderMod"
        data = {'SignalID': SignalID, 
                'StrategyTag':StrategyTag,                 
                'SourceSymbol':SourceSymbol, 
                'TransactionType':TransactionType, 
                'OrderType':OrderType,  
				'Price':Price, 
				'TriggerPrice':TriggerPrice, 
                'Quantity':Quantity,                 
                'SignalLTP':SignalLTP }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
	
    def IB_MappedOrderSimple(self, StrategyTag:str,
                            SourceSymbol:str, 
                            TransactionType:str, 
                            SignalLTP:float=0):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Exit the order by providing as signal id. Order can be exited without providing Signal ID as well in that case order will be exited in FIFO.
        '''
        url = self.source_url + "/MappedOrderSimple"
        data = {'StrategyTag':StrategyTag,                 
                'SourceSymbol':SourceSymbol, 
                'TransactionType':TransactionType,                
                'SignalLTP':SignalLTP }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")	
    
    # Order Placement Methods Implemetation
    def IB_PlaceOrder(self, UniqueID:int, 
                            StrategyTag:str, 
                            UserID:str, 
                            Exchange:str, 
                            Symbol:str, 
                            TransactionType:str, 
                            OrderType:str, 
                            ProductType:str, 
                            Price:float, 
                            TriggerPrice:float, 
                            ProfitValue:str, 
                            StoplossValue:str,
                            Quantity:int, 
                            Validity:str="", 
                            SLTrailingValue:str="", 
                            DisclosedQuantity:str="", 
                            SignalLTP:str="", 
                            DataProvider:str=""):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Cancel / Modify orders(s). If you’re having multiple users enabled, still this request id will be for the whole request and any cancellation etc will be performed for all users.
        '''
        url = self.source_url + "/PlaceOrder"
        data = {'UniqueID': UniqueID, 
                'StrategyTag':StrategyTag, 
                'UserID':UserID, 
                'Exchange':Exchange, 
                'Symbol':Symbol, 
                'TransactionType':TransactionType, 
                'OrderType':OrderType, 
                'Validity':Validity, 
                'ProductType':ProductType, 
                'Quantity':Quantity, 
                'Price':Price, 
                'TriggerPrice':TriggerPrice, 
                'ProfitValue':ProfitValue, 
                'StoplossValue':StoplossValue, 
                'SLTrailingValue':SLTrailingValue, 
                'DisclosedQuantity':DisclosedQuantity, 
                'SignalLTP':SignalLTP, 
                'DataProvider': DataProvider }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_PlaceOrderAdv(self, UniqueID:int,
                               StrategyTag:str, 
                               UserID:str, 
                               Exchange:str, 
                               Symbol:str, 
                               TransactionType:str, 
                               OrderType:str, 
                               ProductType:str,
                               Price:float, 
                               TriggerPrice:float, 
                               ProfitValue:str, 
                               StoplossValue:str,
                               Quantity:int,
                               Validity:str="",
                               SLTrailingValue:str="", 
                               DisclosedQuantity:str="", 
                               DataProvider:str="", 
                               TgtTrailingValue:str="", 
                               BreakEvenPoint:str="", 
                               SignalLTP:str="",  
                               MaxLTPDifference:str="", 
                               PriceSpread:str="", 
                               TriggerSpread:str="", 
                               CancelIfNotCompleteInSeconds:int=5):

        '''
        Description: Function to place order.

            Parameter: Each parameter described in below grid. 

            Return Type: Integer (Request ID)

            On Success:
            Returns the RequestID as an integer which can be used to Cancel / Modify orders(s). If you’re having multiple users enabled, still this request id will be for the whole request and any cancellation etc will be performed for all users.
        '''
        url = self.source_url + "/PlaceOrderAdv"
        data = {'UniqueID': UniqueID, 
                'StrategyTag':StrategyTag, 
                'UserID':UserID, 
                'Exchange':Exchange, 
                'Symbol':Symbol, 
                'TransactionType':TransactionType, 
                'OrderType':OrderType, 
                'Validity':Validity, 
                'ProductType':ProductType, 
                'Quantity':Quantity, 
                'Price':Price, 
                'TriggerPrice':TriggerPrice, 
                'ProfitValue':ProfitValue, 
                'StoplossValue':StoplossValue, 
                'SLTrailingValue':SLTrailingValue, 
                'DisclosedQuantity':DisclosedQuantity,
                'DataProvider': DataProvider,
                'TgtTrailingValue':TgtTrailingValue, 
                'BreakEvenPoint':BreakEvenPoint,
                'SignalLTP':SignalLTP, 
                'MaxLTPDifference':MaxLTPDifference, 
                'PriceSpread':PriceSpread, 
                'TriggerSpread':TriggerSpread, 
                'CancelIfNotCompleteInSeconds':CancelIfNotCompleteInSeconds }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
    

    #Order Modify Functions
    def IB_ModifyOrder(self,RequestID:int, 
                            Price:float, 
                            TriggerPrice:float, 
                            ProfitValue:str, 
                            StoplossValue:str,
                            Quantity:int, 
                            SLTrailingValue:str="", 
                            TgtTrailingValue:str="", 
                            BreakEvenPoint:str=""):
        '''
        Description: Function to modify the open order. It can also be used to modify the Target / SL for BO / CO orders. It is important to note that this function will only work for orders placed through IB_PlaceOrder or IB_PlaceOrderAdv. 

            You can either supply the UniqueID or the Request ID received from IB_PlaceOrder call. This is a mandatory parameter and rest all are optional. 

            Here you can supply the parameter which you actually want to modify and rest others can be set as default values ( Meaning “” for string and 0 for numbers and decimals)

            Parameter: Each parameter described in below grid. 

            Return Type: bool
        '''
        url = self.source_url + "/ModifyOrder"
        data = {'RequestID':RequestID, 
                'Quantity':Quantity, 
                'Price':Price, 
                'TriggerPrice':TriggerPrice, 
                'ProfitValue':ProfitValue, 
                'StoplossValue':StoplossValue, 
                'SLTrailingValue':SLTrailingValue, 
                'TgtTrailingValue':TgtTrailingValue, 
                'BreakEvenPoint':BreakEvenPoint }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    #Order Exit or Cancellation Functions
    def  IB_CancelOrExitOrder(self, RequestID:int):
        '''
        Description: Function to cancel the open order or to exit any running MIS / BO / CO Order.
            You can either supply the UniqueID or the Order ID received from IB_PlaceOrder call. It is important to note that this function will only work for orders placed through IB_PlaceOrder or IB_PlaceOrderAdv. 

            For Simple / MIS Order, this function can be used to cancel the order if that order is still open. If Simple / MIS Order was completed then This function will place a reverse order. Example if the order placed a SELL order then IB_CancelOrExitOrder will place the BUY order for the executed quantity and it will exit if that Order fails if that order was already completed.

            For BO and CO order, this function will cancel the order if order is still open. In case the main order is already completed and their SL / Target orders are still pending then this function will exit the BO / CO Order.

            Return Type: bool

            Imp Note

            If you had enabled Multiple Users in the Bridge then Bridge may have placed multiple orders for a single PlaceOrder call.

            In this case bridge will Cancel / Exit all the associated orders

        '''

        url = self.source_url + "/CancelOrExitOrder"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    #Market Data Functions

    def IB_Subscribe (self, Exchange:str, 
                            Symbol:str, 
                            DataProvider:str=""):
        '''
        Description: Function to Subscribe for the particular symbol in Broker’s Feed. This is a one time activity and do not subscribe every time.

            It is strongly advisable to subscribe for feed before calling IB_LTP etc functions.

            Return Type: void
        '''
        url = self.source_url + "/Subscribe"
        data = {'Exchange': Exchange,
                'Symbol': Symbol,
                'DataProvider': DataProvider }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return
                
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_LTP (self, Exchange:str, 
                      Symbol:str, 
                      DataProvider:str=""):
        '''
        Description: Function to get the Last Trading Price for mentioned Symbol. This function will only work when the broker is providing Market Feed Data. Very first call of the functions may be delayed with a few seconds, however subsequent calls will be much faster.

            Return Type: decimal
            If Success then returns the LTP from Market Feed from Broker, else returns 0.

        '''
        url = self.source_url + "/LTP"
        data = {'Exchange': Exchange,
                'Symbol': Symbol,
                'DataProvider': DataProvider }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
    
    def IB_BID (self, Exchange:str, 
                      Symbol:str, 
                      DataProvider:str=""):
        '''
        Description: Function to get the Best BID Price for mentioned Symbol. This function will only work when the broker is providing Market Feed Data. Very first call of the functions may be delayed with a few seconds, however subsequent calls will be much faster.

            Return Type: decimal
            If Success then returns the Best BID from Market Feed from Broker, else returns 0.

        '''
        url = self.source_url + "/BID"
        data = {'Exchange': Exchange,
                'Symbol': Symbol,
                'DataProvider': DataProvider }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_ASK (self, Exchange:str, 
                      Symbol:str, 
                      DataProvider:str=""):
        '''
        Description: Function to get the Best ASK Price for mentioned Symbol. This function will only work when the broker is providing Market Feed Data. Very first call of the functions may be delayed with a few seconds, however subsequent calls will be much faster.

            Return Type: decimal
            If Success then returns the Best ASK from Market Feed from Broker, else returns 0.

        '''
        url = self.source_url + "/ASK"
        data = {'Exchange': Exchange,
                'Symbol': Symbol,
                'DataProvider': DataProvider }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")
    
    def IB_FeedLTP (self, Exchange:str, 
                          Symbol:str, 
                          LTP, 
                          BID, 
                          ASK,
                          DataProvider:str=""):
        '''
        Description: If Broker is not providing feed and still you wanted to use advanced functionality of Intelligent Bridge, Then you can submit LTP Data from your Charting Platform.

            Return Type: void
        '''
        url = self.source_url + "/FeedLTP"
        data = {'Exchange': Exchange,
                'Symbol': Symbol,
                'DataProvider': DataProvider,
                'LTP': LTP,
                'BID': BID,
                'ASK': ASK }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_OrderID (self, RequestID:int):
        '''
        Description: Function to get the Order ID for provided Unique ID. If orders were placed for more than one user then it will provide comma separated Order IDs for all users.

        Return Type: String
        If Success then returns the Broker Order ID, else returns the empty string.
        For multiple Users, you will get list of comma separated Order IDs
        '''
        url = self.source_url + "/OrderID"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return str(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_LastOrderID (self, UserID:str):
        '''
        Description: Function to get the Order ID for last placed order. It will return the Order ID for the very last order placed.

        Return Type: String
        If Success then returns the Broker Order ID, else returns the empty string.
        '''
        url = self.source_url + "/LastOrderID"
        data = {'UserID': UserID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return str(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_OrderStatus (self, RequestID:int):
        '''
        Description: Function to check the latest status of the Entry Order. If orders were placed for more than one user then it will provide comma separated Order IDs for all users.

        You can either supply the UniqueID or the Request ID received from the Place Order call.

        Return Type: String
        If Success then returns the below given statuses, else returns the empty string.
        For multiple Users, you will get list of comma separated Order IDs

        Possible Status Values
        open
        completed
        rejected
        cancelled

            This gives the status of the whole signal, in case of multiple users it is possible that order may get placed in few and it may get rejected in others. In this case Bridge will give status of signal as completed as order was executed for few users.
        '''
        url = self.source_url + "/OrderStatus"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return str(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_OrderQty (self, OrderID:int):
        '''
        Description: Function to get the Quantity of the order.

        Return Type: Integer
        If Success then returns the Quantity used while placing the order, else returns the 0.
        For multiple Users, this will return Order Qty for very first user.
        '''
        url = self.source_url + "/OrderQty"
        data = {'OrderID': OrderID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_OrderFilledQty (self, OrderID:int):
        '''
        Description: Function to get the Filled Quantity of the very first order of signal. Filled Quantity is the actual quantity which is actually executed against the order. Eg we placed an order for 100 qty but till now we received only 25 qty then this function will return only 25.

        Return Type: Integer
        If Success then returns the Filled Quantity, else returns the 0.
        For multiple Users, this will return Filled Order Qty for very first user.
        '''
        url = self.source_url + "/OrderFilledQty"
        data = {'OrderID': OrderID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return int(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_OrderAvgPrice (self, OrderID:int):
        '''
        Description: Function to get the Average execution price of the very first Entry Order of the signal. If order is still open then this function will return 0.

        Return Type: Decimal
        If Success then returns the Avg Price, else returns the 0.
        For multiple Users, this will return Avg Price for the very first user.
        '''
        url = self.source_url + "/OrderAvgPrice"
        data = {'OrderID': OrderID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return float(response.json()['response'])

        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_IsOrderOpen (self, RequestID:int):
        '''
        Description: Function to check the status of the first Entry Order of signal, if that is still open. For CO and BO orders it will check only for Main Order.

        Return Type: bool
        If order is still open then true otherwise false.
        For multiple Users, this will check and return status for very first order placed for a signal.
        '''
        url = self.source_url + "/IsOrderOpen"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_IsOrderRejected (self, RequestID:int):
        '''
        Description: Function to check the status of the  first Entry Order of signal, if that is Rejected. For CO and BO orders it will check only for Main Order.

        Return Type: bool
        If the order is rejected then true otherwise false.
        For multiple Users, this will check and return status for very first order placed for a signal.
        '''
        url = self.source_url + "/IsOrderRejected"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_IsOrderCompleted (self, RequestID:int):
        '''
        Description: Function to check the status of the  first Entry Order of signal, if that is Completed. For CO and BO orders it will check only for Main Order.

        Return Type: bool
        If the order is completed then true otherwise false.
        For multiple Users, this will check and return status for very first order placed for a signal.
        '''
        url = self.source_url + "/IsOrderCompleted"
        data = {'RequestID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO:: Host Server Not Reachable")

    def IB_IsOrderCancelled (self, RequestID:int):
        '''
        Description: Function to check the status of the  first Entry Order of signal, if that is cancelled. For CO and BO orders it will check only for Main Order.

        Return Type: bool
        If the order is cancelled then true otherwise false.
        For multiple Users, this will check and return status for very first order placed for a signal.
        '''

        url = self.source_url + "/IsOrderCancelled"
        data = {'UniqueID': RequestID }
        try:
            response = requests.post(url, data=data)
            if(self._Check_Status(response)):
                return True
            else:
                return False
        
        except ValueError as er:
            print(er.args)
        except:
            print("LOG_INFO::  Host Server Not Reachable")