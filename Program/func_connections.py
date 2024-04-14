'''
Connect to DYDX Client
'''

from v4_client_py.clients import Subaccount, IndexerClient
from v4_client_py.clients.constants import Network

from constants import DYDX_MNEMONIC


# Connect to DYDX CompositeClient
def connect_to_dydx():

    # Create client
    client = IndexerClient(
    config=Network.config_network().indexer_config,
   )
    subaccount = Subaccount.from_mnemonic(DYDX_MNEMONIC)
    address = subaccount.address
    print(address)
    print(subaccount)
    print("Connection successful")

    # Return Client
    return client
