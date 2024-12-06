from decimal import Decimal
from injective_functions.base import InjectiveBase
from typing import Dict, List
from injective_functions.utils.indexer_requests import fetch_decimal_denoms
from injective_functions.utils.helpers import detailed_exception_info
from pyinjective.proto.cosmos.bank.v1beta1 import (
    bank_pb2 as bank_pb,
    tx_pb2 as cosmos_bank_tx_pb,
)
from pyinjective.proto.cosmos.base.v1beta1 import coin_pb2 as base_coin_pb


class InjectiveBank(InjectiveBase):
    def __init__(self, chain_client) -> None:
        # Initializes the network and the composer
        super().__init__(chain_client)

    async def transfer_funds(
        self, amount: Decimal, denom: str = None, to_address: str = None
    ) -> Dict:
        await self.chain_client.init_client()

        msg = self.chain_client.composer.MsgSend(
            from_address=self.chain_client.address.to_acc_bech32(),
            to_address=str(to_address),
            amount=float(amount),
            denom=denom,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)

    async def query_balances(self, denom_list: List[str] = None) -> Dict:
        await self.chain_client.init_client()
        try:

            denoms: Dict[str, int] = await fetch_decimal_denoms(
                self.chain_client.network_type
            )
            bank_balances = await self.chain_client.client.fetch_bank_balances(
                address=self.chain_client.address.to_acc_bech32()
            )
            bank_balances = bank_balances["balances"]

            # hash the bank balances as a kv pair
            human_readable_balances = {}
            for token in bank_balances:
                if token["denom"] in denoms:
                    human_readable_balances[token["denom"]] = str(
                        int(token["amount"]) / 10 ** int(denoms[token["denom"]])
                    )
            # check if denom is an arg fron the openai func calling
            filtered_balances = dict()
            if denom_list != None:
                # filter the balances
                # TODO: replace with lambda func
                for denom in denom_list:
                    if denom in human_readable_balances:
                        filtered_balances[denom] = human_readable_balances[denom]
                    else:
                        filtered_balances[denom] = "The token is not on mainnet!"
                return {"success": True, "result": filtered_balances}

            else:
                return {"success": True, "result": human_readable_balances}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def query_spendable_balances(self, denom_list: List[str] = None) -> Dict:
        await self.chain_client.init_client()
        try:
            denoms: Dict[str, int] = await fetch_decimal_denoms(
                self.chain_client.network_type
            )
            bank_balances = await self.chain_client.client.fetch_spendable_balances(
                address=self.chain_client.address.to_acc_bech32()
            )
            bank_balances = bank_balances["balances"]
            # hash the bank balances as a kv pair
            human_readable_balances = {
                token["denom"]: str(
                    int(token["amount"]) / 10 ** int(denoms[token["denom"]])
                )
                for token in bank_balances
                if token["denom"] in denoms
            }

            # check if denom is an arg fron the openai func calling
            filtered_balances = dict()
            if denom_list != None:
                # filter the balances
                # TODO: replace with lambda func
                for denom in denom_list:
                    if denom in human_readable_balances:
                        filtered_balances[denom] = human_readable_balances[denom]
                    else:
                        filtered_balances[denom] = "The token is not on mainnet!"
                return {"success": True, "result": filtered_balances}

            else:
                return {"success": True, "result": human_readable_balances}

        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def query_total_supply(self, denom_list: List[str] = None) -> Dict:
        await self.chain_client.init_client()
        try:
            # we request this over and over again because new tokens can be added
            denoms: Dict[str, int] = await fetch_decimal_denoms(
                self.chain_client.network
            )
            total_supply = await self.chain_client.client.fetch_total_supply()
            total_supply = total_supply["supply"]
            human_readable_supply = {
                token["denom"]: str(
                    int(token["amount"]) / 10 ** int(denoms[token["denom"]])
                )
                for token in total_supply
                if token["denom"] in denoms
            }

            # check if denom is an arg fron the openai func calling
            filtered_supply = dict()
            if denom_list != 0:
                # filter the balances
                # TODO: replace with lambda func
                for denom in denom_list:
                    if denom in human_readable_supply:
                        filtered_supply[denom] = human_readable_supply[denom]
                    else:
                        filtered_supply[denom] = "The token is not on mainnet!"
                return {"success": True, "result": filtered_supply}

            else:
                return {"success": True, "result": human_readable_supply}

        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def query_balance_of_denom(self, denom: str) -> Dict:
        await self.chain_client.init_client()

        try:

            metadata = await self.chain_client.client.fetch_denom_metadata(denom)
            decimals = metadata["metadata"]["decimals"]

            bank_balance = await self.chain_client.client.fetch_bank_balance(
                address=self.chain_client.address.to_acc_bech32(), denom=denom
            )

            balance = bank_balance["balance"]["amount"]

            formatted = int(balance) / 10 ** int(decimals)

            return {"success": True, "result": str(formatted)}

        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def send_airdrop(self, denom, airdrop_amounts):
        await self.chain_client.init_client()

        try:
            metadata = await self.chain_client.client.fetch_denom_metadata(denom)
            decimals = metadata["metadata"]["decimals"]

            total_amount = sum(
                int(float(record["amount"]) * (10**decimals))
                for record in airdrop_amounts
            )

            inputs = [
                {
                    "address": self.chain_client.address.to_acc_bech32(),
                    "coins": [
                        base_coin_pb.Coin(
                            denom=denom,
                            amount=str(total_amount),
                        )
                    ],
                }
            ]

            outputs = []
            for record in airdrop_amounts:
                output = {
                    "address": record["address"],
                    "coins": [
                        base_coin_pb.Coin(
                            denom=denom,
                            amount=str(int(float(record["amount"]) * (10**decimals))),
                        )
                    ],
                }
                outputs.append(output)

            msg = cosmos_bank_tx_pb.MsgMultiSend(inputs=inputs, outputs=outputs)

            # Broadcast the transaction
            res = await self.chain_client.build_and_broadcast_tx(msg)
            return {"success": True, "result": res}

        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}
