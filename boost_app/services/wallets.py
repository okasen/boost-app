from typing import List

from bson import ObjectId
from fastapi import Depends

from boost_app.dto import Wallet, NewWalletRequest, PyObjectId, WalletType, DonatableWallet, LoanWallet, \
    TransferRequest, TransferResponse, TransferStatus, AdjustRequest, BalanceAction, TransferAdminRequest
from boost_app.errors import InvalidWalletTypeError, WalletBalanceError, TransferRequestError
from boost_app.repositories.wallets import WalletRepository


class WalletService:
    def __init__(self, wallet_repository: WalletRepository = Depends()) -> None:
        self.wallet_repository = wallet_repository

    def get_wallet(self, wallet_id: PyObjectId) -> Wallet:
        wallet_id = ObjectId(wallet_id)
        wallet = self.wallet_repository.get_by_id(wallet_id=wallet_id)
        return wallet

    def get_wallets_for_user(self, user_id: PyObjectId) -> List[Wallet]:
        user_id = ObjectId(user_id)
        wallets = self.wallet_repository.get_by_user_id(user_id=user_id)
        return wallets

    def create_wallet(self, request: NewWalletRequest) -> Wallet:
        if request.type == WalletType.DONATABLE_FUNDS:
            wallet = DonatableWallet(user_id=request.user_id,
                                     type=request.type,
                                     donations_given=[])
        elif request.type == WalletType.LOAN_BALANCE:
            wallet = LoanWallet(user_id=request.user_id,
                                type=request.type,
                                loans=[],
                                donations=[])
        else:
            raise InvalidWalletTypeError("Invalid wallet type entered")
        request = self.wallet_repository.create_wallet(new_wallet=wallet)
        return request

    def adjust_balance(self, wallet_id: PyObjectId, request: AdjustRequest) -> Wallet:
        wallet_id = ObjectId(wallet_id)
        wallet = self.wallet_repository.get_by_id(wallet_id=wallet_id)
        if request.action == BalanceAction.INCREASE:
            wallet.total_balance = wallet.total_balance + request.amount
        elif request.action == BalanceAction.DECREASE and wallet.total_balance >= request.amount:
            wallet.total_balance = wallet.total_balance - request.amount
        else:
            raise WalletBalanceError("Error: Cannot decrease wallet into negative balance")
        updated_wallet = self.wallet_repository.update_wallet(wallet=wallet)
        return updated_wallet

    def update_request(self, transfer_id: PyObjectId, request: TransferAdminRequest) -> TransferRequest:
        transfer_id = ObjectId(transfer_id)
        transfer_request = self.wallet_repository.get_transfer_request(transfer_id=transfer_id)
        if transfer_request.status == TransferStatus.COMPLETED:
            raise TransferRequestError(f"Transfer {transfer_id} has already been completed and cannot be updated.")
        transfer_request.status = request.new_status
        transfer_update_result = self.wallet_repository.update_transfer_request(request=transfer_request)
        if transfer_update_result.status == TransferStatus.APPROVED:
            approve_result = self.transfer_funds_between_wallets(request=transfer_request)
            return approve_result.original_request

        return transfer_update_result

    def get_transfer_request(self, transfer_id: PyObjectId) -> TransferRequest:
        transfer_id = ObjectId(transfer_id)
        request = self.wallet_repository.get_transfer_request(transfer_id=transfer_id)
        return request

    def request_funds_transfer(self, request: TransferRequest) -> TransferResponse:
        source_wallet = self.wallet_repository.get_by_id(wallet_id=ObjectId(request.source_wallet_id))
        target_wallet = self.wallet_repository.get_by_id(wallet_id=ObjectId(request.target_wallet_id))

        source_wallet_holder = source_wallet.user_id
        target_wallet_holder = target_wallet.user_id

        if source_wallet.type != WalletType.DONATABLE_FUNDS or target_wallet.type != WalletType.LOAN_BALANCE:
            return TransferResponse(
                current_status=TransferStatus.DENIED,
                message="Transfers must be from a donatable funds wallet to a loan wallet"
            )

        if source_wallet_holder == target_wallet_holder:
            return TransferResponse(
                current_status=TransferStatus.DENIED,
                message="Users may not transfer funds between their own wallets"
            )

        if source_wallet_holder != request.initiator_user:
            return TransferResponse(
                current_status=TransferStatus.DENIED,
                message="Initiator user must be owner of the source wallet"
            )
        
        if source_wallet.total_balance >= request.amount:
            try:
                transfer = self.wallet_repository.create_transfer_request(request=request)
                return TransferResponse(
                    transfer_id=transfer.id,
                    current_status=TransferStatus.SUBMITTED,
                    original_request=transfer
                )
            except RuntimeError:
                return TransferResponse(
                    current_status=TransferStatus.DENIED,
                    message="Transfer request failed due to an internal server error, please try again later."
                )
        else:
            return TransferResponse(
                current_status=TransferStatus.DENIED,
                message="Source wallet does not have enough funds to cover transfer amount."
            )

    def transfer_funds_between_wallets(self, request: TransferRequest) -> TransferResponse:
        source_wallet_request = AdjustRequest(
            action=BalanceAction.DECREASE,
            amount=request.amount
        )
        target_wallet_request = AdjustRequest(
            action=BalanceAction.INCREASE,
            amount=request.amount
        )
        try:
            self.adjust_balance(wallet_id=request.source_wallet_id, request=source_wallet_request)
        except RuntimeError as e:
            raise WalletBalanceError(f"Failed updating source wallet in donation request. Original error {str(e)}")
        try:
            self.adjust_balance(wallet_id=request.target_wallet_id, request=target_wallet_request)
        except RuntimeError as e:
            fix_source_action = AdjustRequest(
                action=BalanceAction.INCREASE,
                amount=request.amount
            )
            self.adjust_balance(wallet_id=request.source_wallet_id, request=fix_source_action)
            raise WalletBalanceError(f"Failed updating target wallet. Source wallet rolled back. Original error {str(e)}")
        request.status = TransferStatus.COMPLETED
        self.wallet_repository.update_transfer_request(request=request)
        return TransferResponse(
            transfer_id=request.id,
            current_status=TransferStatus.COMPLETED,
            original_request=request
        )