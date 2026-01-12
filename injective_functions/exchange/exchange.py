from decimal import Decimal
from injective_functions.base import InjectiveBase
from injective_functions.utils.indexer_requests import (
    fetch_decimal_denoms,
    normalize_ticker,
)
from injective_functions.utils.helpers import (
    impute_market_id,
    impute_market_ids,
    detailed_exception_info,
    to_human_readable,
)
from pyinjective.client.model.pagination import PaginationOption

from typing import Dict, List


class InjectiveExchange(InjectiveBase):
    def __init__(self, chain_client) -> None:
        # Initializes the network and the composer
        super().__init__(chain_client)

    async def get_subaccount_deposits(
        self, subaccount_idx: int, denoms: List[str] = None
    ) -> Dict:
        try:

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            deposits_response = (
                await self.chain_client.client.fetch_subaccount_deposits(
                    subaccount_id=subaccount_id
                )
            )
            deposits = deposits_response["deposits"]
            denom_decimals = await fetch_decimal_denoms(self.chain_client.network_type)
            human_readable_deposits = {}
            # checks if the denoms are specified
            if denoms:
                # iterate through the specified denoms
                for denom in denoms:
                    # Corner case 1: denom might not be in deposits found in chain data a case when gpt function calling parses wrong args
                    if denom in deposits and denom in denom_decimals:
                        human_readable_deposits[denom] = {
                            "available_balance": str(
                                int(deposits[denom]["availableBalance"])
                                / 10 ** int(denom_decimals[denom])
                            ),
                            "total_balance": str(
                                int(deposits[denom]["totalBalance"])
                                / 10 ** int(denom_decimals[denom])
                            ),
                        }
                    else:
                        human_readable_deposits[denom] = {
                            "available_balance": "balance not found",
                            "total_balance": "balance not found",
                        }
            # Otherwise we iterate through all the denoms
            else:
                for denom, deposit in deposits.items():
                    if denom in denom_decimals:
                        human_readable_deposits[denom] = {}
                        human_readable_deposits[denom]["available_balance"] = str(
                            int(deposit["availableBalance"])
                            / 10 ** denom_decimals[denom]
                        )

                        human_readable_deposits[denom]["total_balance"] = str(
                            int(deposit["totalBalance"]) / 10 ** denom_decimals[denom]
                        )
            return {"success": True, "result": human_readable_deposits}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_aggregate_market_volumes(self, market_ids=List[str]) -> Dict:
        try:
            market_ids = await impute_market_ids(market_ids)
            res = await self.chain_client.client.fetch_aggregate_market_volumes(
                market_ids=market_ids
            )
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_aggregate_account_volumes(
        self, market_ids: List[str], addresses: List[str]
    ) -> Dict:
        try:
            market_ids = await impute_market_ids(market_ids)
            res = await self.chain_client.client.fetch_aggregate_volumes(
                accounts=addresses,
                market_ids=market_ids,
            )
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_subaccount_orders_spot(
        self, subaccount_idx: int, market_id: str
    ) -> Dict:
        try:
            market_id = await impute_market_id(market_id)

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)

            print(
                f"Fetching orders for subaccount {subaccount_id} in market {market_id}"
            )
            orders = (
                await self.chain_client.client.fetch_chain_account_address_spot_orders(
                    account_address=self.chain_client.address.to_acc_bech32(),
                    market_id=market_id,
                )
            )
            print(f"Orders fetched: {orders}")
            return {"success": True, "result": orders}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_historical_orders(self, market_id: str) -> Dict:

        try:
            market_id = await impute_market_id(market_id)

            res = await self.chain_client.client.fetch_historical_trade_records(
                market_id=market_id
            )
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_mid_price_and_tob_derivatives_market(self, market_id: str) -> Dict:
        try:
            # 1. Fetch market info to get the decimal precision
            market_info_response = await self.getMarketInfo(market_id)
            if not market_info_response.get("success"):
                raise ValueError(
                    f"Failed to fetch market info: {market_info_response.get('error')}"
                )

            # Extract the quote decimals needed for price conversion
            market_data = market_info_response["result"]["market"]["market"]
            quote_decimals = market_data["quoteDecimals"]

            # Impute the market ID for the next call
            imputed_market_id = await impute_market_id(market_id)

            # 2. Fetch the raw, large-integer price data
            raw_price_data = (
                await self.chain_client.client.fetch_derivative_mid_price_and_tob(
                    market_id=imputed_market_id,
                )
            )
            print(f"Raw price data: {raw_price_data}")

            # 3. Convert each price value using the quote_decimals
            human_readable_prices = {}
            for key, value in raw_price_data.items():
                # All values in this response are prices, so they all use quote_decimals
                human_readable_prices[key] = to_human_readable(value, quote_decimals)

            # Optionally, convert to strings for clean JSON output
            human_readable_prices_str = {
                k: str(v) for k, v in human_readable_prices.items()
            }

            return {"success": True, "result": human_readable_prices_str}

        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_mid_price_and_tob_spot_market(self, market_id: str) -> Dict:
        try:
            market_id = await impute_market_id(market_id)

            res = await self.chain_client.client.fetch_spot_mid_price_and_tob(
                market_id=market_id,
            )
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_derivatives_orderbook(
        self, market_id: str, limit: int = None
    ) -> Dict:
        try:
            market_id = await impute_market_id(market_id)
            pagination = PaginationOption(limit)
            orderbook = await self.chain_client.client.fetch_chain_derivative_orderbook(
                market_id=market_id,
                pagination=pagination,
            )
            return {"success": True, "result": orderbook}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_spot_orderbook(self, market_id: str, limit: int = None) -> Dict:
        try:
            market_id = await impute_market_id(market_id)
            pagination = PaginationOption(limit)
            orderbook = await self.chain_client.client.fetch_chain_spot_orderbook(
                market_id=market_id,
                pagination=pagination,
            )
            return {"success": True, "result": orderbook}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def trader_derivative_orders(self, market_id: str, subaccount_idx: int):
        try:

            market_id = await impute_market_id(market_id)

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            orders = await self.chain_client.client.fetch_chain_account_address_derivative_orders(
                market_id=market_id,
                account_address=self.chain_client.address.to_acc_bech32(),
            )
            return {"success": True, "result": orders}
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}

    async def trader_spot_orders(self, market_id: str, subaccount_idx: int):
        try:
            market_id = await impute_market_id(market_id)

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            orders = await self.chain_client.client.fetch_chain_trader_spot_orders(
                market_id=market_id,
                subaccount_id=subaccount_id,
            )
            return {"success": True, "result": orders}
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}

    async def trader_derivative_orders_by_hash(
        self, market_id: str, subaccount_idx: int, order_hashes: List[str]
    ) -> Dict:
        try:
            market_id = await impute_market_id(market_id)

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            orders = (
                await self.chain_client.client.fetch_chain_derivative_orders_by_hashes(
                    market_id=market_id,
                    subaccount_id=subaccount_id,
                    order_hashes=order_hashes,
                )
            )
            return {"success": True, "result": orders}
        except Exception as e:
            return {"success": False, "result": detailed_exception_info(e)}

    async def trader_spot_orders_by_hash(
        self, market_id: str, subaccount_idx: int, order_hashes: List[str]
    ) -> Dict:
        try:
            market_id = await impute_market_id(market_id)

            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            orders = await self.chain_client.client.fetch_chain_spot_orders_by_hashes(
                market_id=market_id,
                subaccount_id=subaccount_id,
                order_hashes=order_hashes,
            )
            return {"success": True, "result": orders}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def getMarketInfo(self, market_id: str) -> Dict:
        try:
            ticker = normalize_ticker(market_id)
            market_id = await impute_market_id(market_id)
            isPerp = "PERP" in ticker

            if isPerp:
                market_info = (
                    await self.chain_client.client.fetch_chain_derivative_market(
                        market_id=market_id
                    )
                )
            else:
                market_info = await self.chain_client.client.fetch_chain_spot_market(
                    market_id=market_id
                )

            return {"success": True, "result": market_info}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def get_subaccount_position_in_market(
        self,
        market_id: str,
        subaccount_idx: int,
    ) -> Dict:
        try:
            print(f"Fetching position and PnL for market: {market_id}")

            # 1. Get market info to find decimals AND the current mark price
            market_info_response = await self.getMarketInfo(market_id)
            if not market_info_response.get("success"):
                raise ValueError(
                    f"Failed to fetch market info: {market_info_response.get('error')}"
                )

            print(f"Market info: {market_info_response}")
            market_result = market_info_response["result"]
            market_data = market_result["market"]["market"]

            # Extract necessary data for conversions and calculations
            quote_decimals = market_data["quoteDecimals"]
            base_decimals = 18  # Standard for base assets like INJ
            raw_mark_price = market_result["market"]["markPrice"]

            print(f"Raw mark price: {raw_mark_price}, quote decimals: {quote_decimals}")

            # Impute market_id for the next call
            imputed_market_id = await impute_market_id(market_id)
            subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
            print(f"Subaccount ID: {subaccount_id}, market ID: {imputed_market_id}")

            # 2. Get the raw position data
            positions_response = await self.chain_client.client.fetch_chain_subaccount_effective_position_in_market(
                subaccount_id=subaccount_id, market_id=imputed_market_id
            )
            print(f"API Response: {positions_response}")

            position_state = positions_response.get("state")

            if position_state:
                # 3. Convert all raw values to human-readable Decimals
                quantity = to_human_readable(position_state["quantity"], base_decimals)
                entry_price = to_human_readable(
                    position_state["entryPrice"], quote_decimals + base_decimals
                )
                margin = to_human_readable(
                    position_state["effectiveMargin"], quote_decimals + base_decimals
                )
                current_price = to_human_readable(
                    raw_mark_price, quote_decimals + base_decimals
                )

                print(
                    f"Calculating PnL: Current={current_price}, Entry={entry_price}, Qty={quantity}, Margin={margin}"
                )

                # 4. Calculate PnL based on position direction
                pnl_quote = Decimal("0")
                if position_state["isLong"]:
                    pnl_quote = (current_price - entry_price) * quantity
                else:  # Position is Short
                    pnl_quote = (entry_price - current_price) * quantity

                # 5. Calculate Percentage PnL
                pnl_percent = Decimal("0")
                if margin > 0:
                    pnl_percent = (pnl_quote / margin) * 100

                # 6. Build the final, comprehensive result object
                human_readable_result = {
                    "ticker": market_data["ticker"],
                    "isLong": position_state["isLong"],
                    "quantity": quantity,
                    "entryPrice": entry_price,
                    "effectiveMargin": margin,
                    "currentMarkPrice": current_price,
                    "pnl_quote": pnl_quote,  # PnL in the quote asset (e.g., USDT)
                    "pnl_percent": pnl_percent,  # PnL as a percentage of margin
                }

                print(f"Position details: {human_readable_result}")

                # Optionally convert to strings for clean JSON output before returning
                result_str = {
                    k: f"{v:.4f}" if isinstance(v, Decimal) else v
                    for k, v in human_readable_result.items()
                }

                return {"success": True, "result": result_str}
            else:
                print(
                    f"No position found for subaccount {subaccount_id} in market {imputed_market_id}."
                )
                return {
                    "success": True,
                    "result": "No open position found in this market.",
                }

        except Exception as e:
            print(
                f"An error occurred in get_subaccount_position_in_market: {e}",
                exc_info=True,
            )
            return {"success": False, "error": detailed_exception_info(e)}

    async def launch_instant_spot_market(
        self,
        ticker: str,
        base: str,
        quote: str,
        min_price_tick: str,
        min_quantity_tick: str,
        min_notional: str,
    ) -> Dict:
        try:
            await self.chain_client.init_client()
            msg = self.chain_client.composer.msg_instant_spot_market_launch(
                sender=self.chain_client.address.to_acc_bech32(),
                ticker=ticker,
                base_denom=base,
                quote_denom=quote,
                min_price_tick_size=Decimal(min_price_tick),
                min_quantity_tick_size=Decimal(min_quantity_tick),
                min_notional=Decimal(min_notional),
            )
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def launch_instant_perp_market(
        self,
        ticker: str,
        quote_denom: str,
        oracle_base: str,
        oracle_quote: str,
        oracle_scale_factor: int,
        oracle_type: str,
        maker_fee_rate: str,
        taker_fee_rate: str,
        initial_margin_ratio: str,
        maintenance_margin_ratio: str,
        min_price_tick: str,
        min_quantity_tick: str,
        min_notional_size: str,
    ) -> Dict:
        try:

            await self.chain_client.init_client()
            msg = self.chain_client.composer.msg_instant_perpetual_market_launch(
                sender=self.chain_client.address.to_acc_bech32(),
                ticker=ticker,
                quote_denom=quote_denom,
                oracle_base=oracle_base,
                oracle_quote=oracle_quote,
                oracle_scale_factor=oracle_scale_factor,
                oracle_type=oracle_type,
                maker_fee_rate=Decimal(maker_fee_rate),
                taker_fee_rate=Decimal(taker_fee_rate),
                initial_margin_ratio=Decimal(initial_margin_ratio),
                maintenance_margin_ratio=Decimal(maintenance_margin_ratio),
                min_price_tick_size=Decimal(min_price_tick),
                min_quantity_tick_size=Decimal(min_quantity_tick),
                min_notional=Decimal(min_notional_size),
            )
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": detailed_exception_info(e)}

    async def opt_out_trade_earn_rewards(self) -> Dict:

        msg = self.chain_client.composer.msg_rewards_opt_out(
            sender=self.chain_client.address.to_acc_bech32()
        )
        await self.chain_client.build_and_broadcast_tx(msg)
