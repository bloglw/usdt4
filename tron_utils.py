import tronpy
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from config import tron_node
from database import get_all_users, update_balance, update_available_balance, add_recharge_record, mark_recharges_processed, get_unprocessed_recharges
import requests

client = tronpy.Tron(provider=HTTPProvider(tron_node))

# USDT在TRON网络上的合约地址
USDT_CONTRACT_ADDRESS = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

def generate_deposit_address():
    priv_key = PrivateKey.random()
    address = priv_key.public_key.to_base58check_address()
    return address, priv_key.hex()

def get_trc20_balance(address):
    url = f"https://api.trongrid.io/v1/accounts/{address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            trc20_tokens = data['data'][0].get('trc20', [])
            for token in trc20_tokens:
                if USDT_CONTRACT_ADDRESS in token:
                    return float(token[USDT_CONTRACT_ADDRESS]) / 1_000_000
    return 0

def monitor_deposits():
    users = get_all_users()
    for user in users:
        user_id, address, private_key, balance, available_balance, frozen_balance = user
        try:
            current_balance = get_trc20_balance(address)

            # 检测当前余额与数据库中的余额差异
            if current_balance > balance:
                recharge_amount = current_balance - balance
                # 记录充值信息
                add_recharge_record(user_id, recharge_amount)
            
            # 获取并处理未处理的充值记录
            new_recharges = get_unprocessed_recharges(user_id)
            for recharge in new_recharges:
                recharge_amount = recharge[2]  # 获取金额
                update_available_balance(user_id, recharge_amount)
            
            # 更新balance为最新值
            update_balance(user_id, current_balance)
            # 标记充值记录为已处理
            mark_recharges_processed(user_id)

        except Exception as e:
            print(f"Error monitoring deposits for {address}: {e}")

def get_latest_balance(address):
    """获取用户地址的最新余额"""
    try:
        return get_trc20_balance(address)
    except Exception as e:
        print(f"Error getting latest balance for {address}: {e}")
        return 0
