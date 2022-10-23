import json
from typing import Any, Dict, List

from bson import json_util, ObjectId
from pymongo import MongoClient

from boost_app.dto import Wallet, WalletType, DonatableWallet, LoanWallet, TransferRequest
from boost_app.errors import InvalidWalletTypeError


class WalletRepository:
    def __init__(self) -> None:
        mongo = MongoClient()
        finances_db = mongo.finances
        self.user_wallets = finances_db.wallets
        self.transfers = finances_db.transfers

    @staticmethod
    def _deserialize_transfer(transfer: Dict[str, Any]) -> TransferRequest:
        transfer_id = transfer.pop("_id")
        initiator_user = transfer.pop("initiator_user")
        source_wallet_id = transfer.pop("source_wallet_id")
        target_wallet_id = transfer.pop("target_wallet_id")
        transfer.pop("id")
        transfer_dict = json.loads(json_util.dumps(transfer))

        return TransferRequest(
            id=transfer_id,
            initiator_user=initiator_user,
            source_wallet_id=source_wallet_id,
            target_wallet_id=target_wallet_id,
            amount=transfer_dict["amount"],
            submitted=transfer_dict["submitted"],
            status=transfer_dict["status"],
        )
    

    @staticmethod
    def _deserialize_wallet(wallet: Dict[str, Any]) -> Wallet:
        wallet_id = wallet.pop("_id")
        user_id = wallet.pop("user_id")
        wallet.pop("id")
        wallet_dict = json.loads(json_util.dumps(wallet))
        wallet_dict["_id"] = str(wallet_id)
        wallet_dict["user_id"] = str(user_id)

        try:
            if wallet_dict["type"] == str(WalletType.DONATABLE_FUNDS):
                return DonatableWallet(
                    id=wallet_id,
                    user_id=user_id,
                    type=WalletType.DONATABLE_FUNDS,
                    donations_given=wallet_dict["donations_given"],
                    total_balance=wallet_dict["total_balance"],
                    created=wallet_dict["created"],
                    last_updated=wallet_dict["last_updated"]
                )
            elif wallet_dict["type"] == str(WalletType.LOAN_BALANCE):
                return LoanWallet(
                    id=wallet_id,
                    user_id=user_id,
                    type=WalletType.LOAN_BALANCE,
                    loans=wallet_dict["loans"],
                    donations=wallet_dict["donations"],
                    total_balance=wallet_dict["total_balance"],
                    created=wallet_dict["created"],
                    last_updated=wallet_dict["last_updated"]
                )
            else:
                raise InvalidWalletTypeError("Wallet is not a valid type")
        except KeyError as e:
            if "type" in str(e):
                raise InvalidWalletTypeError("Wallet has no type")

    def get_by_id(self, wallet_id: ObjectId) -> Wallet:
        wallet = self.user_wallets.find_one(wallet_id)

        wallet = self._deserialize_wallet(wallet=wallet)

        return wallet

    def get_by_user_id(self, user_id: ObjectId) -> List[Wallet]:
        wallet_list = []
        for wallet in self.user_wallets.find({"user_id": str(user_id)}):
            try:
                wallet = self._deserialize_wallet(wallet=wallet)
                wallet_list.append(wallet)
            except InvalidWalletTypeError as e:
                print(f"encountered an invalid wallet type: {str(e)}")
        return wallet_list

    def create_wallet(self, new_wallet: Wallet) -> Wallet:
        wallet_dict = new_wallet.dict()
        wallet_dict["type"] = str(wallet_dict["type"])
        created_id = self.user_wallets.insert_one(wallet_dict).inserted_id
        created_wallet = self.user_wallets.find_one(created_id)

        wallet = self._deserialize_wallet(wallet=created_wallet)

        return wallet

    def update_wallet(self, wallet: Wallet) -> Wallet:
        wallet_dict = wallet.dict()
        wallet_dict["type"] = str(wallet_dict["type"])
        self.user_wallets.replace_one({"_id": ObjectId(wallet.id)}, wallet_dict)
        updated_wallet = self.user_wallets.find_one(ObjectId(wallet.id))
        wallet = self._deserialize_wallet(wallet=updated_wallet)

        return wallet

    def create_transfer_request(self, request: TransferRequest) -> TransferRequest:
        request_dict = request.dict()
        created_id = self.transfers.insert_one(request_dict).inserted_id
        created_request = self.transfers.find_one(created_id)

        request = self._deserialize_transfer(transfer=created_request)

        return request

    def get_transfer_request(self, transfer_id: ObjectId) -> TransferRequest:
        request = self.transfers.find_one(transfer_id)

        request = self._deserialize_transfer(transfer=request)

        return request

    def update_transfer_request(self, request: TransferRequest) -> TransferRequest:
        transfer_dict = request.dict()
        transfer_dict["status"] = str(transfer_dict["status"])
        self.transfers.replace_one({"_id": ObjectId(request.id)}, transfer_dict)
        updated_transfer = self.transfers.find_one(ObjectId(request.id))
        transfer = self._deserialize_transfer(transfer=updated_transfer)

        return transfer