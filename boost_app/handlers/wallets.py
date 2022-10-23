from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends

from boost_app.dto import Wallet, NewWalletRequest, PyObjectId, TransferRequest, AdjustRequest, TransferAdminRequest
from boost_app.encoders import JSONEncoder
from boost_app.services.wallets import WalletService


router = APIRouter(
    prefix="/wallets",
    tags=["wallets"],
)


@router.get("/users/{user_id}")
async def get_wallets_for_user(user_id: PyObjectId, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    wallets = [wallet.dict() for wallet in wallet_service.get_wallets_for_user(user_id=user_id)]
    return {"wallets": wallets}


@router.get("/{wallet_id}")
async def get_wallet_with_id(wallet_id: PyObjectId, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    wallet = wallet_service.get_wallet(wallet_id=wallet_id)
    return {"wallet": wallet.dict()}


@router.patch("/funds/{wallet_id}")
async def adjust_wallet_funds(wallet_id: PyObjectId, request: AdjustRequest, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    response = wallet_service.adjust_balance(wallet_id=wallet_id, request=request)
    return {"response": response}


@router.post("/")
async def create_wallet(request: NewWalletRequest, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    created_wallet = wallet_service.create_wallet(request=request)
    return {"wallet": created_wallet.dict()}


@router.post("/transfers")
async def request_transfer_funds(request: TransferRequest, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    transfer_response = wallet_service.request_funds_transfer(request=request)
    return {"response": transfer_response.dict()}


@router.get("/transfers/{transfer_id}")
async def check_transaction_status(transfer_id: PyObjectId, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    response = wallet_service.get_transfer_request(transfer_id=transfer_id)
    return {"response": response}


@router.patch("/transfers/{transfer_id}")
async def update_transfer_status(transfer_id: PyObjectId, request: TransferAdminRequest, wallet_service: WalletService = Depends()) -> Dict[str, Any]:
    admin_response = wallet_service.update_request(transfer_id=transfer_id, request=request)
    return {"response": admin_response.dict()}