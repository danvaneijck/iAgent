from typing import Dict
from injective_functions.base import InjectiveBase
from injective_functions.utils.helpers import detailed_exception_info
import json
import base64

from pyinjective.proto.cosmos.bank.v1beta1 import tx_pb2 as cosmos_bank_tx_pb
from pyinjective.proto.cosmos.base.v1beta1 import coin_pb2 as base_coin_pb


class DojoAMMFactory(InjectiveBase):
    def __init__(self, chain_client) -> None:
        super().__init__(chain_client)

        self.dojo_factory = "inj1pc2vxcmnyzawnwkf03n2ggvt997avtuwagqngk"

    async def dojo_whitelist_native_token(self, denom: str, decimals: int) -> Dict:
        try:
            if "factory" not in denom:
                return {
                    "success": False,
                    "error": {
                        "message": f"Please provide the factory denom",
                    },
                }

            await self.chain_client.init_client()

            coin = base_coin_pb.Coin(amount="1", denom=denom)

            msg_send = cosmos_bank_tx_pb.MsgSend(
                from_address=self.chain_client.address.to_acc_bech32(),
                to_address=self.dojo_factory,
                amount=[coin],
            )

            # Prepare the message dynamically
            msg_content = {
                "add_native_token_decimals": {"denom": denom, "decimals": decimals}
            }

            msg_whitelist = self.chain_client.composer.MsgExecuteContract(
                sender=self.chain_client.address.to_acc_bech32(),
                contract=self.dojo_factory,
                msg=json.dumps(msg_content),
            )

            # Broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast(
                [msg_send, msg_whitelist]
            )
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def dojo_create_liquidity_pool(
        self,
        denom1: str,
        denom2: str,
        is_cw20_asset1: bool = False,
        is_cw20_asset2: bool = False,
    ) -> Dict:
        """
        Create a liquidity pool with specified token denominations, supporting native or CW20 tokens.

        Args:
            denom1 (str): Denomination or contract address of the first token.
            denom2 (str): Denomination or contract address of the second token.
            is_cw20_asset1 (bool): Whether the first asset is a CW20 token.
            is_cw20_asset2 (bool): Whether the second asset is a CW20 token.

        Returns:
            Dict: Result of the transaction.
        """
        try:
            await self.chain_client.init_client()

            # Determine asset definitions based on whether they are CW20 or native
            asset1_info = (
                {"token": {"contract_addr": denom1}}
                if is_cw20_asset1
                else {"native_token": {"denom": denom1}}
            )
            asset2_info = (
                {"token": {"contract_addr": denom2}}
                if is_cw20_asset2
                else {"native_token": {"denom": denom2}}
            )

            # Prepare the message
            msg_content = {
                "create_pair": {
                    "assets": [
                        {
                            "info": asset1_info,
                            "amount": "0",
                        },
                        {
                            "info": asset2_info,
                            "amount": "0",
                        },
                    ],
                },
            }

            msg = self.chain_client.composer.MsgExecuteContract(
                sender=self.chain_client.address.to_acc_bech32(),
                contract=self.dojo_factory,
                msg=json.dumps(msg_content),
            )

            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def provide_liquidity_on_dojo(
        self,
        pair_address: str,
        token1_denom: str,
        token1_amount: str,
        token2_denom: str,
        token2_amount: str,
        is_token1_cw20: bool = False,
        is_token2_cw20: bool = False,
    ) -> Dict:
        """
        Provide liquidity to a pair with support for CW20 and native tokens.

        Args:
            pair_address (str): Address of the liquidity pair contract.
            token1_denom (str): Denomination or contract address of the first token.
            token1_amount (str): Amount of the first token.
            token2_denom (str): Denomination or contract address of the second token.
            token2_amount (str): Amount of the second token.
            is_token1_cw20 (bool): Whether the first token is a CW20 token.
            is_token2_cw20 (bool): Whether the second token is a CW20 token.

        Returns:
            Dict: Result of the transaction.
        """
        try:
            await self.chain_client.init_client()

            # Determine token info
            token1_info = (
                {"token": {"contract_addr": token1_denom}}
                if is_token1_cw20
                else {"native_token": {"denom": token1_denom}}
            )
            token2_info = (
                {"token": {"contract_addr": token2_denom}}
                if is_token2_cw20
                else {"native_token": {"denom": token2_denom}}
            )

            # Prepare the message
            msg_content = {
                "provide_liquidity": {
                    "assets": [
                        {
                            "info": token1_info,
                            "amount": token1_amount,
                        },
                        {
                            "info": token2_info,
                            "amount": token2_amount,
                        },
                    ],
                },
            }

            # Prepare funds if a native token is involved
            funds = (
                [{"denom": token1_denom, "amount": token1_amount}]
                if not is_token1_cw20
                else []
            )
            if not is_token2_cw20:
                funds.append({"denom": token2_denom, "amount": token2_amount})

            msg = self.chain_client.composer.MsgExecuteContract(
                sender=self.chain_client.address.to_acc_bech32(),
                contract=pair_address,
                msg=json.dumps(msg_content),
                funds=funds,
            )

            # Broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_dojo_pair_info(self, pair: str) -> Dict:
        try:
            await self.chain_client.init_client()

            query_msg = {"pair": {}}

            pair_info = await self.chain_client.client.fetch_smart_contract_state(
                address=pair, query_data=json.dumps(query_msg)
            )

            return {"success": True, "result": pair_info}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def dojo_trade_assets_from_pair(
        self,
        pair_address: str,
        offer_asset_address: str,
        amount: float,
        max_spread: float = 2.0,
    ) -> Dict:
        """
        Buy an asset from a DojoSwap liquidity pair.

        Args:
            pair_address (str): Address of the liquidity pair contract.
            offer_asset_address (str): Address of the asset being offered (denom for native, contract address for CW20).
            amount (float): The amount of the asset to swap.
            max_spread (float): Maximum allowable price slippage (default is 2%).

        Returns:
            Dict: Result of the transaction.
        """
        try:
            # Validate inputs
            if not pair_address:
                raise ValueError("Pair address is required.")
            if not offer_asset_address:
                raise ValueError("Offer asset address is required.")
            if amount <= 0:
                raise ValueError("A valid amount greater than 0 is required.")

            await self.chain_client.init_client()

            # Fetch pair info to determine the asset type and decimals
            query_msg = {"pair": {}}
            pair_info_response = (
                await self.chain_client.client.fetch_smart_contract_state(
                    address=pair_address, query_data=json.dumps(query_msg)
                )
            )
            pair_info_base64 = pair_info_response["data"]
            pair_info_json = base64.b64decode(pair_info_base64).decode("utf-8")
            pair_info = json.loads(pair_info_json)

            # Extract asset_infos and decimals
            asset_infos = pair_info.get("asset_infos", [])
            asset_decimals = pair_info.get("asset_decimals", [])

            if len(asset_infos) != 2 or len(asset_decimals) != 2:
                raise ValueError("Unexpected pair info structure.")

            # Find the asset and corresponding decimals
            offer_asset_info = None
            decimals = None

            for i, asset_info in enumerate(asset_infos):
                if (
                    "native_token" in asset_info
                    and asset_info["native_token"]["denom"] == offer_asset_address
                ):
                    offer_asset_info = {"native_token": {"denom": offer_asset_address}}
                    decimals = asset_decimals[i]
                    break
                elif (
                    "token" in asset_info
                    and asset_info["token"]["contract_addr"] == offer_asset_address
                ):
                    offer_asset_info = {"token": {"contract_addr": offer_asset_address}}
                    decimals = asset_decimals[i]
                    break

            if not offer_asset_info:
                raise ValueError("Offer asset address not found in pair info.")

            # Adjust the amount based on decimals
            adjusted_amount = int(amount * (10**decimals))

            if "native_token" in offer_asset_info:
                # Native token operations
                swap_operations = {
                    "swap": {
                        "offer_asset": {
                            "info": offer_asset_info,
                            "amount": str(adjusted_amount),
                        },
                        "max_spread": str(max_spread),
                    },
                }

                # Prepare funds for native tokens
                funds = [{"denom": offer_asset_address, "amount": str(adjusted_amount)}]

                msg = self.chain_client.composer.MsgExecuteContract(
                    sender=self.chain_client.address.to_acc_bech32(),
                    contract=pair_address,
                    msg=json.dumps(swap_operations),
                    funds=funds,
                )

            else:
                # CW20 token operations
                swap_operations = {
                    "send": {
                        "contract": pair_address,
                        "amount": str(adjusted_amount),
                        "msg": base64.b64encode(
                            json.dumps({"swap": {}}).encode("utf-8")
                        ).decode("utf-8"),
                    },
                }

                msg = self.chain_client.composer.MsgExecuteContract(
                    sender=self.chain_client.address.to_acc_bech32(),
                    contract=offer_asset_address,  # CW20 contract address
                    msg=json.dumps(swap_operations),
                )

            # Broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])

            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}
