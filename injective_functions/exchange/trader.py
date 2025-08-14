import uuid
from decimal import Decimal
from injective_functions.base import InjectiveBase
from injective_functions.utils.helpers import impute_market_id, base64convert


class InjectiveTrading(InjectiveBase):
    def __init__(self, chain_client) -> None:
        super().__init__(chain_client)

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
        # converted_order_hash = base64convert(order_hash)
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
