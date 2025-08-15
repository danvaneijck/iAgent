import uuid
from decimal import Decimal
from injective_functions.base import InjectiveBase
from injective_functions.utils.helpers import (
    impute_market_id,
    to_human_readable,
    detailed_exception_info,
)
from injective_functions.utils.indexer_requests import (
    normalize_ticker,
)
from typing import Dict
import asyncio


class InjectiveTrading(InjectiveBase):
    def __init__(self, chain_client) -> None:
        super().__init__(chain_client)

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

    async def place_derivative_limit_order(
        self,
        price: float,
        quantity: float,
        side: str,
        market_id: str,
        subaccount_idx: int,
        leverage: str,
    ):
        """Place a limit order"""
        market_id = await impute_market_id(market_id)
        self.subaccount_id = self.chain_client.address.get_subaccount_id(
            index=subaccount_idx
        )
        msg = self.chain_client.composer.msg_create_derivative_limit_order(
            sender=self.chain_client.address.to_acc_bech32(),
            fee_recipient=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=self.subaccount_id,
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            margin=self.chain_client.composer.calculate_margin(
                quantity=Decimal(str(quantity)),
                price=Decimal(str(price)),
                leverage=Decimal(leverage),
                is_reduce_only=False,
            ),
            order_type=side,
            cid=str(uuid.uuid4()),
        )

        return await self.chain_client.build_and_broadcast_tx(msg)

    async def place_derivative_market_order(
        self,
        quantity: float,
        side: str,
        market_id: str,
        subaccount_idx: int,
        leverage: str,
    ):
        """Place a market order"""

        market_id = await impute_market_id(market_id)
        self.subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        # For market orders, we'll use the current price as an estimate
        # this gets bbo and mid from composer.
        estimated_price = (
            await self.chain_client.client.fetch_derivative_mid_price_and_tob(
                market_id=market_id
            )["midPrice"]
        )

        msg = self.chain_client.composer.msg_create_derivative_market_order(
            sender=self.chain_client.address.to_acc_bech32(),
            fee_recipient=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=self.subaccount_id,
            price=Decimal(estimated_price),
            quantity=Decimal(str(quantity)),
            margin=self.chain_client.composer.calculate_margin(
                quantity=Decimal(str(quantity)),
                price=Decimal(estimated_price),
                leverage=Decimal(leverage),
                is_reduce_only=False,
            ),
            order_type=side,
            cid=str(uuid.uuid4()),
        )

        return await self.chain_client.build_and_broadcast_tx(msg)

    async def cancel_derivative_limit_order(
        self, market_id: str, subaccount_idx: int, order_hash: str
    ):
        market_id = await impute_market_id(market_id)
        # converted_order_hash = base64convert(order_hash)
        converted_order_hash = order_hash

        subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        print(
            f"Canceling order with hash: {converted_order_hash} at subaccount {subaccount_id} in market {market_id}"
        )

        order = await self.chain_client.client.fetch_chain_derivative_orders_by_hashes(
            market_id=market_id,
            subaccount_id=subaccount_id,
            order_hashes=[converted_order_hash],
        )
        print(f"Order details: {order}")
        order = order.get("orders", [])[0] if order else None
        isBuy = order["isBuy"]
        print(f"Order isBuy status: {isBuy}")

        msg = self.chain_client.composer.msg_cancel_derivative_order(
            sender=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=subaccount_id,
            order_hash=converted_order_hash,
            is_buy=isBuy,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)

    async def place_spot_limit_order(
        self,
        price: float,
        quantity: float,
        side: str,
        market_id: str,
        subaccount_idx: int,
    ):
        """Place a limit order"""

        market_id = await impute_market_id(market_id)
        self.subaccount_id = self.chain_client.address.get_subaccount_id(
            index=subaccount_idx
        )
        msg = self.chain_client.composer.msg_create_spot_limit_order(
            sender=self.chain_client.address.to_acc_bech32(),
            fee_recipient=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=self.subaccount_id,
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            order_type=side,
            cid=str(uuid.uuid4()),
        )

        return await self.chain_client.build_and_broadcast_tx(msg)

    async def place_spot_market_order(
        self, quantity: float, side: str, market_id: str, subaccount_idx: int
    ):
        """Place a market order"""
        market_id = await impute_market_id(market_id)
        self.subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)

        price_data = await self.chain_client.client.fetch_spot_mid_price_and_tob(
            market_id=market_id
        )

        if not price_data or "midPrice" not in price_data:
            raise ValueError(
                f"Could not fetch a valid mid-price for spot market {market_id}"
            )

        if side.lower() == "buy":
            estimated_price = price_data["bestSellPrice"]
            print(f"Placing MARKET BUY. Using best ask price: {estimated_price}")
        elif side.lower() == "sell":
            estimated_price = price_data["bestBuyPrice"]
            print(f"Placing MARKET SELL. Using best bid price: {estimated_price}")
        else:
            raise ValueError(
                f"Invalid order side provided: '{side}'. Must be 'buy' or 'sell'."
            )

        msg = self.chain_client.composer.msg_create_spot_market_order(
            sender=self.chain_client.address.to_acc_bech32(),
            fee_recipient=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=self.subaccount_id,
            price=Decimal(estimated_price),
            quantity=Decimal(str(quantity)),
            order_type=side,
            cid=str(uuid.uuid4()),
        )

        return await self.chain_client.build_and_broadcast_tx(msg)

    async def cancel_spot_limit_order(
        self, market_id: str, subaccount_idx: int, order_hash: str
    ):
        converted_order_hash = order_hash
        print(f"Canceling spot order with hash: {converted_order_hash}")
        market_id = await impute_market_id(market_id)
        subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        print(f"Canceling order for subaccount {subaccount_id} in market {market_id}")
        msg = self.chain_client.composer.msg_cancel_spot_order(
            sender=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=subaccount_id,
            order_hash=converted_order_hash,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)

    async def poll_for_tx_status(
        self, tx_hash: str, timeout: int = 30, delay: int = 2
    ) -> Dict:
        """
        Polls the chain for a transaction's final status until it's confirmed or a timeout is reached.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                tx_response = await self.chain_client.client.fetch_tx(tx_hash)
                if tx_response:
                    final_status = tx_response.get("txResponse", {})

                    if final_status:
                        code = final_status.get("code")
                        if code == 0:
                            print(
                                f"Transaction {tx_hash} confirmed successfully in block {final_status.get('height')}."
                            )
                            return {"status": "Success", "data": tx_response}
                        else:
                            error_log = final_status.get(
                                "raw_log",
                                "Execution failed without a specific message.",
                            )
                            print(
                                f"Transaction {tx_hash} failed with code {code}: {error_log}"
                            )
                            return {
                                "status": "Failed",
                                "reason": error_log,
                                "data": tx_response,
                            }

            except Exception as e:
                print(f"Polling for {tx_hash}... Not found yet.")
                pass

            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"Timeout reached waiting for transaction {tx_hash}.")
                return {
                    "status": "Timeout",
                    "reason": "Transaction not found on-chain within the time limit.",
                }

            await asyncio.sleep(delay)

    async def close_derivative_position_market(
        self, market_id: str, subaccount_idx: int
    ):
        """
        Closes an entire derivative position at the current market price.
        """
        market_info = await self.getMarketInfo(market_id)
        market_id = await impute_market_id(market_id)

        subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)

        print("Closing derivative position at market price...")
        positions_response = await self.chain_client.client.fetch_chain_subaccount_effective_position_in_market(
            subaccount_id=subaccount_id, market_id=market_id
        )
        print(f"API Response: {positions_response}")

        position_data = positions_response.get("state")
        quantity_to_close = to_human_readable(position_data["quantity"], 18)
        is_long = position_data["isLong"]

        side_to_close = "sell" if is_long else "buy"
        print(
            f"Current position is {'LONG' if is_long else 'SHORT'} {quantity_to_close}. Placing a market {side_to_close.upper()} order to close."
        )

        price_data = await self.chain_client.client.fetch_derivative_mid_price_and_tob(
            market_id=market_id
        )
        print(f"Price data: {price_data}")

        quote_decimals = market_info["result"]["market"]["market"]["quoteDecimals"]
        print(f"Quote decimals: {quote_decimals}")

        price_scaling_factor = quote_decimals + 18
        raw_closing_price = (
            price_data["bestBuyPrice"]
            if side_to_close == "sell"
            else price_data["bestSellPrice"]
        )
        closing_price = to_human_readable(raw_closing_price, price_scaling_factor)
        entry_price = to_human_readable(
            position_data["entryPrice"], price_scaling_factor
        )
        margin = to_human_readable(
            position_data["effectiveMargin"], price_scaling_factor
        )

        pnl_quote = Decimal("0")
        if is_long:
            pnl_quote = (closing_price - entry_price) * quantity_to_close
        else:
            pnl_quote = (entry_price - closing_price) * quantity_to_close

        pnl_percent = (pnl_quote / margin) * 100 if margin > 0 else Decimal("0")

        worst_price_human = closing_price

        print(
            f"Placing market order to close position at worst price: {worst_price_human}"
        )

        msg = self.chain_client.composer.msg_create_derivative_market_order(
            sender=self.chain_client.address.to_acc_bech32(),
            fee_recipient=self.chain_client.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=subaccount_id,
            quantity=Decimal(str(quantity_to_close)),
            price=Decimal(str(worst_price_human)),
            order_type=side_to_close.upper(),
            margin=self.chain_client.composer.calculate_margin(
                quantity=Decimal(str(quantity_to_close)),
                price=Decimal(worst_price_human),
                leverage=Decimal(1),
                is_reduce_only=True,
            ),
            cid=str(uuid.uuid4()),
        )

        print(f"Closing position with message: {msg}")

        tx_response = await self.chain_client.build_and_broadcast_tx(msg)
        tx_hash = tx_response["result"]["txResponse"]["txhash"]

        print(
            f"Transaction broadcasted with hash: {tx_hash}. Polling for on-chain confirmation..."
        )

        final_tx_status = await self.poll_for_tx_status(tx_hash)

        print(f"Final transaction status: {final_tx_status}")

        final_report = {
            "status": final_tx_status["status"],
            "ticker": market_info["result"]["market"]["market"]["ticker"],
            "side": "Long" if is_long else "Short",
            "quantity": f"{quantity_to_close:.4f}",
            "entryPrice": f"{entry_price:.4f}",
            "closingPrice_approx": f"{closing_price:.4f}",
            "pnl_quote": f"{pnl_quote:.4f}",
            "pnl_percent": f"{pnl_percent:.2f}%",
            "transactionDetails": tx_response,
        }

        tx_response = await self.chain_client.client.fetch_tx(tx_hash)

        print(f"Final report: {final_report}")

        return {"success": True, "result": final_report}
