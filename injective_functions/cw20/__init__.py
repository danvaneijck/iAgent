from typing import Dict
from injective_functions.base import InjectiveBase
from injective_functions.utils.helpers import detailed_exception_info
import json
import base64


class CW20Factory(InjectiveBase):
    def __init__(self, chain_client) -> None:
        super().__init__(chain_client)

    async def increase_cw20_allowance(
        self, token_address: str, spender_address: str, amount: str
    ) -> Dict:
        """
        Increase the allowance of a CW20 token for a contract.

        Args:
            token_address (str): Address of the CW20 token contract.
            spender_address (str): Address of the contract to spend the token.
            amount (str): Amount to increase the allowance by.

        Returns:
            Dict: Result of the transaction.
        """
        try:
            await self.chain_client.init_client()

            # Prepare the message
            msg_content = {
                "increase_allowance": {
                    "spender": spender_address,
                    "amount": amount,
                    "expires": {"never": {}},
                }
            }

            msg = self.chain_client.composer.MsgExecuteContract(
                sender=self.chain_client.address.to_acc_bech32(),
                contract=token_address,
                msg=json.dumps(msg_content),
            )

            # Broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}

    async def get_cw20_token_info(self, token_address: str) -> Dict:
        """
        Fetch information about a CW20 token.

        Args:
            token_address (str): Address of the CW20 token contract.

        Returns:
            Dict: Token information such as name, symbol, decimals, and total supply.
        """
        try:
            await self.chain_client.init_client()

            query_msg = {"token_info": {}}

            token_info = await self.chain_client.client.fetch_smart_contract_state(
                address=token_address, query_data=json.dumps(query_msg)
            )

            return {"success": True, "result": token_info}
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}

    async def get_cw20_token_balance(self, token_address: str) -> Dict:
        """
        Fetch the balance of a CW20 token for the current wallet address.

        Args:
            token_address (str): Address of the CW20 token contract.

        Returns:
            Dict: Token balance.
        """
        try:
            # Initialize the blockchain client
            await self.chain_client.init_client()

            token_info_query = {"token_info": {}}
            token_info_response = (
                await self.chain_client.client.fetch_smart_contract_state(
                    address=token_address, query_data=json.dumps(token_info_query)
                )
            )

            token_info_base64 = token_info_response["data"]
            token_info_json = base64.b64decode(token_info_base64).decode("utf-8")
            token_info_data = json.loads(token_info_json)
            decimals = token_info_data.get("decimals", 0)

            balance_query = {
                "balance": {"address": self.chain_client.address.to_acc_bech32()}
            }

            balance_response = (
                await self.chain_client.client.fetch_smart_contract_state(
                    address=token_address, query_data=json.dumps(balance_query)
                )
            )

            balance_base64 = balance_response["data"]
            balance_json = base64.b64decode(balance_base64).decode("utf-8")
            balance_data = json.loads(balance_json)
            raw_balance = int(balance_data.get("balance", "0"))

            # Adjust balance using decimals
            formatted_balance = raw_balance / (10**decimals)

            return {
                "success": True,
                "result": {
                    "raw_balance": raw_balance,
                    "formatted_balance": formatted_balance,
                    "decimals": decimals,
                },
            }
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}
