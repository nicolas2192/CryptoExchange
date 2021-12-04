# Nicolas Cortinas. December 4th, 2021
# Simple Crypto Exchange running on the Ethereum Network.

# TO DO:
# -- Add a sell function.
# -- Add Argparse features.

# IMPORTS
import json
import requests
import datetime
from web3 import Web3


# Main class ExchangeSession
class ExchangeSession(object):
    """
    Single User Session. With this object the user will be able to check its account balance, make transactions, etc.
    
    Parameters:
        cred_path: String. Credentials JSON file path.
        address_account: String. User's address account.
    
    Returns:
        Session object instantiated.
    """
    
    def __init__(self, cred_path, address_account):
        """
        Init method.
        
        Parameters:
            cred_path: String. Credentials JSON file path.
            address_account: String. User's address account.
            
        Returns:
            Instance of the class.
        """
        
        self.credentials = self.load_credentials(cred_path)
        self.account = address_account
        self.infura = self.infura_connection(self.credentials["infura_url"])
        self.balance_wei = None
        self.balance_eth = None
        self.balance_fiat = None
        
        self.init_time = datetime.datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S")
        
        
    def __repr__(self):
        """
        repr method.
        """
        
        # Returns when the class was instantiated.
        return self.init_time
    
    
    def load_credentials(self, cred_path) -> dict:
        """
        Load credentials from a JSON file.

        Parameters:
            cred_path: String. Credentials JSON file path.

        Returns:
            Dictionary with credentials. E.g.:
            {'infura_url': 'https://mainnet.infura.io/v3/YOUR_API_KEY',
            'cryptocompare_api': 'YOUR_API_KEY', 'etherscan_api': 'YOUR_API_KEY'}
        """
        
        try:
            with open(cred_path, "r") as f:
                cred = json.load(f)
            return cred
        except Exception as json_file_error:
            print("Error loading credentials JSON file:", str(json_file_error))
    
    
    def infura_connection(self, infura_url) -> Web3:
        """
        Create a Web3 connection object to infura.

        Parameters:
            infura_url: String. Infura URL with api key. E.g.: 'https://mainnet.infura.io/v3/YOUR_API_KEY'

        Returns:
            Web3 connection object
        """

        try:
            # Connecting to the network.
            con = Web3(Web3.HTTPProvider(infura_url))
        except Exception as infura_error:
            print("Infura connection error", str(infura_error))

        # Checking if the connection was successful.
        if con.isConnected():
            print("Infura... OK!")
            return con
        else:
            print("Infura... Error!")
    
    
    def get_exchange_rates(self, curr_from, curr_to) -> dict:
        """
        Creates CyptoCompare API URL to fetch crypto and fiat exchanges.

        Parameters:
            curr_from: List. List of crypto currencies to be used as a base. This is the currency of your account. E.g:. ["ETH"]
            curr_to: List. List of crypto and/or fiat currencies to be used as a quote. e.g:. ["BTC", "USD", "EUR"]
        Returns:
            Dictionary with requested exchanges. E.g.:
            {'ETH': {'BTC': 0.08326, 'USD': 4002.57, 'EUR': 3560.39}}
        """

        # Turning lists into strings.
        curr_from = ",".join([x.upper() for x in curr_from])
        curr_to = ",".join([x.upper() for x in curr_to])
 
        # Generating api url.
        api_key = self.credentials["cryptocompare_api"]
        cc_api_url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={curr_from}&tsyms={curr_to}&api_key={api_key}"

        try: 
            # Requesting data and returning it as a dictionary.
            r = requests.get(cc_api_url)
            return r.json()
        except Exception as cryptocompare_error:
            print("CryptoCompare Error:", str(cryptocompare_error))
            
    
    def get_gas(self) -> dict:
        """
        Fetch current gas price from EtherScan.io API

        Parameters:
            api_key: String. API key.
            
        Returns: 
            Dictionary with the Safe, Propose and Fast gas price. E.g.:
            {'units_gwei': 
             {'SafeGasPrice': '117', 'ProposeGasPrice': '118', 'FastGasPrice': '120'},
            'units_wei': 
             {'SafeGasPrice': 117000000000, 'ProposeGasPrice': 118000000000, 'FastGasPrice': 120000000000},
            'units_ether': 
             {'SafeGasPrice': Decimal('1.17E-7'), 'ProposeGasPrice': Decimal('1.18E-7'), 'FastGasPrice': Decimal('1.2E-7')}}
        """

        # Create EtherScan API url.
        api_key = self.credentials["etherscan_api"]
        etherscan_api_url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={api_key}"

        # Fetch data.
        r = requests.get(etherscan_api_url).json()["result"]
        gas_fees = {"units_gwei": {"SafeGasPrice": r["SafeGasPrice"], 
                             "ProposeGasPrice": r["ProposeGasPrice"], 
                             "FastGasPrice": r["FastGasPrice"]}}

        # Update dict with wei value
        gas_wei = {k: self.infura.toWei(v, "gwei") for k, v in gas_fees["units_gwei"].items()}
        gas_fees["units_wei"] = gas_wei

        # Update dict with ether value
        gas_ether = {k: self.infura.fromWei(v, "ether") for k, v in gas_fees["units_wei"].items()}
        gas_fees["units_ether"] = gas_ether

        return gas_fees
    
    
    def compute_transaction_fee(self, fiat_symbol, fiat_value=None):
        """
        Compute transaction fee.

        Parameters:
            fiat_symbol: String. Fiat currency symbol. e.g.: "EUR"
            fiat_value: Float/None. Default None. Fiat currency value as a quote.

        Returns:
            Gas fee dictionary with additional key:value pair: Safe, Propose and Fast fee in the especified fiat currency.
        """
        # Retrieve latest gas price values.
        gas_fees = self.get_gas()

        # This is the fixed gas fee per transaction.
        fixed_gas_fee = 21000 

        # If the fiat value is not provided, it will be fetched.
        if not fiat_value:     
            fiat_value = self.get_exchange_rates(["ETH"], [fiat_symbol])["ETH"][fiat_symbol.upper()]
            
        # Converting ether into fiat currency
        gas_fiat = {f"{k}_{fiat_symbol}": float(v) * fiat_value * fixed_gas_fee for k, v in gas_fees["units_ether"].items()}
        gas_fees[f"units_{fiat_symbol}"] = gas_fiat
        return gas_fees
            
            
    def latest_block(self) -> int:
        """
        Retrieve and display the number of the latest block added to the blockchain.
        
        Parameters:
            None
        
        Returns:
            latest_block: Integer. Lastest Block.
        """

        latest_block = self.infura.eth.blockNumber
        return latest_block
    
    
    def get_balance(self, quote_curr=None) -> dict:
        """
        Retrieve the balance of an account. Assume ETH as Base Currency.
        
        Parameters:
            quote_curr. String/None. Default None. Quote Currency to convert the ETH balance. If None, only returns ETH.
        
        Returns:
            Dictionary with WEI, ETH and Conversion (if applicable). E.g.:
            {'WEI': 2708724165582763, 'ETH': 0.002708724165582763, 'USD': 11.01583943659198}
        """
        
        # Retrieve balance in WEI and convert it into ETH.
        self.balance_wei = self.infura.eth.get_balance(self.account)
        self.balance_eth = float(self.infura.fromWei(self.balance_wei, "ether"))
        
        # If quote_curr, fetchs exchange rate.
        if quote_curr:
            
            try:
                # Fetch current ETH/XXX exchange, convert it and return dictionary with WEI, ETH and Fiat.
                eth_quote_rate = self.get_exchange_rates(["ETH"], [quote_curr])["ETH"][quote_curr.upper()]
                self.balance_fiat = self.balance_eth * eth_quote_rate
                
                return {"WEI": self.balance_wei, "ETH": self.balance_eth, quote_curr: self.balance_fiat}
            
            except Exception as cryptocompare_error:
                
                print("CryptoCompare Error:", str(cryptocompare_error))
                return None
        else:
            return {"WEI": self.balance_wei, "ETH": self.balance_eth}


if __name__ == '__main__':
    
    # Loading Credentials
    creds = "data/credentials.json"
    
    # Initializing 
    account_address = "0xDA8bB5Cf55C5aD7ebf64f24d5eb3fa95B5921230"
    sess = ExchangeSession(creds, account_address)
    print("\nAccount address:", sess.account)
    
    # Fetch account's balance in dollars
    print("\nAccount Balance USD:", sess.get_balance("USD"))
    
    # Fetch last block
    print("\nLatest block:", sess.latest_block())
    
    # Retrieve multiple exchanges
    print("\nTest exchanges:", sess.get_exchange_rates(["ETH", "BTC"], ["BTC", "ETH", "USD", "EUR"]))
    
    # Compute current gas price and transaction fee
    print("\nGas price and Transaction fee in USD:", sess.compute_transaction_fee("USD"))

    print("\nProcess Completed.")
