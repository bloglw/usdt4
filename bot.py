from telethon import TelegramClient, events, Button
import config
from database import add_user, get_user, update_balance, update_available_balance, init_db
from tron_utils import generate_deposit_address, monitor_deposits, get_latest_balance
from datetime import datetime

# 初始化数据库
init_db()

client = TelegramClient('usdt_bot', config.api_id, config.api_hash).start(bot_token=config.bot_token)

# 存储提币请求的状态
withdraw_requests = {}

@client.on(events.NewMessage)
async def handler(event):
    user_id = event.message.sender_id
    text = event.message.text.lower()

    if text == '/start':
        await handle_start(event, user_id)
    elif text == '/deposit':
        await handle_deposit(event, user_id)
    elif text == '/withdraw':
        await handle_withdraw_initiate(event, user_id)
    elif text.isdigit():
        await handle_withdraw(event, user_id, text)
    elif user_id in withdraw_requests and 'amount' in withdraw_requests[user_id] and 'address' not in withdraw_requests[user_id]:
        await address_handler(event)

@client.on(events.CallbackQuery)
async def callback(event):
    user_id = event.sender_id
    data = event.data.decode('utf-8')

    if data == 'deposit':
        await handle_deposit(event, user_id)
    elif data == 'withdraw':
        await handle_withdraw_initiate(event, user_id)
    elif data == 'cancel':
        await handle_withdraw_cancel(event, user_id)
    elif data == 'confirm_withdraw':
        await handle_withdraw_confirm(event, user_id)
    elif data == 'withdraw_all':
        await handle_withdraw_all(event, user_id)
    elif data.startswith('set_amount_'):
        amount = float(data.split('_')[2])
        withdraw_requests[user_id]['amount'] = amount
        await event.respond('请输入您的提币地址：')

async def handle_start(event, user_id):
    user = get_user(user_id)
    if user:
        # 获取用户地址
        address = user[1]
        # 获取最新余额并更新数据库
        latest_balance = get_latest_balance(address)
        update_balance(user_id, latest_balance)
        
        available_balance = user[4]
        frozen_balance = user[5]
        welcome_message = f"""
        欢迎使用USDT钱包机器人！
        可用余额：{available_balance} USDT
        冻结余额：{frozen_balance} USDT
        """
    else:
        welcome_message = "欢迎使用USDT钱包机器人！"

    buttons = [
        [Button.inline("充值", b"deposit")],
        [Button.inline("提币", b"withdraw")]
    ]
    await event.respond(welcome_message, buttons=buttons)

async def handle_deposit(event, user_id):
    user = get_user(user_id)
    if not user:
        address, priv_key = generate_deposit_address()
        add_user(user_id, address, priv_key)
    else:
        address = user[1]
    await event.respond(f'您的充值地址是：`{address}`\n请单击以复制。', parse_mode='markdown')

async def handle_withdraw(event, user_id, text):
    try:
        amount = float(text)
        user = get_user(user_id)
        available_balance = float(user[4]) if user else 0

        if amount > available_balance:
            await event.respond('余额不足以完成申请，请修改提币金额。')
        else:
            if user_id in withdraw_requests:
                withdraw_requests[user_id]['amount'] = amount
                await event.respond('请输入您的提币地址：')
    except ValueError:
        await event.respond('无效的提币金额，请输入有效的数字。')

async def handle_withdraw_initiate(event, user_id):
    user = get_user(user_id)
    available_balance = float(user[4]) if user else 0
    if available_balance < 11:
        await event.respond('最低提币金额为10 USDT + 1 USDT手续费，请保证账户余额不低于11 USDT。')
    else:
        await event.respond('请回复提币数量（例如：10）：', buttons=[
            [Button.inline("提现全部余额", b"withdraw_all")],
            [Button.inline("取消提币", b"cancel")]
        ])
        withdraw_requests[user_id] = {}

async def handle_withdraw_all(event, user_id):
    user = get_user(user_id)
    available_balance = float(user[4]) if user else 0
    if available_balance >= 11:
        withdraw_requests[user_id]['amount'] = available_balance - 1
        await event.respond('请输入您的提币地址：')
    else:
        await event.respond('最低提币金额为10 USDT + 1 USDT手续费，请保证账户余额不低于11 USDT。')

async def handle_withdraw_cancel(event, user_id):
    if user_id in withdraw_requests:
        del withdraw_requests[user_id]
    await handle_start(event, user_id)

async def address_handler(event):
    user_id = event.sender_id
    if user_id in withdraw_requests and 'amount' in withdraw_requests[user_id] and 'address' not in withdraw_requests[user_id]:
        address = event.message.text
        withdraw_requests[user_id]['address'] = address
        amount = withdraw_requests[user_id]['amount']
        await event.respond(f"提币总览:\n数量：{amount} USDT\n地址：`{address}`\n", buttons=[
            [Button.inline("确定", b"confirm_withdraw")],
            [Button.inline("取消", b"cancel")]
        ], parse_mode='markdown')

async def handle_withdraw_confirm(event, user_id):
    if user_id in withdraw_requests:
        amount = withdraw_requests[user_id]['amount']
        address = withdraw_requests[user_id]['address']
        user = get_user(user_id)
        available_balance = float(user[4]) if user else 0
        if available_balance >= (amount + 1):
            update_available_balance(user_id, -(amount + 1))
            await event.respond('提币成功，请等待区块确认！')
            user_info = await client.get_entity(user_id)
            username = user_info.username
            user_name = f"{user_info.first_name} {user_info.last_name}" if user_info.last_name else user_info.first_name
            user_link = f'<a href="tg://user?id={user_id}">{user_name} @{username} {user_id}</a>'
            admin_message = f'{user_link} 提交了提币申请：\n数量：{amount} USDT\n地址：`{address}`\n时间：{datetime.now()}'
            for admin_id in config.admin_user_ids:
                await client.send_message(admin_id, admin_message, parse_mode='html')
            del withdraw_requests[user_id]
        else:
            await event.respond('余额不足以完成此次提币申请。')
            await handle_withdraw_cancel(event, user_id)

# 启动监测
import asyncio
async def monitor_task():
    while True:
        monitor_deposits()
        await asyncio.sleep(60)  # 每分钟监测一次

loop = asyncio.get_event_loop()
loop.create_task(monitor_task())
client.start()
client.run_until_disconnected()
