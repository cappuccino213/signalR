#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time : 2022/4/24 20:30 
# @Author : zhangyp
# @File : MIS_class.py

import logging
import asyncio
import random
import string

from uuid import uuid4
from faker import Faker

from signalrcore_async.hub_connection_builder import HubConnectionBuilder

# 声明日志格式
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
handler = logging.StreamHandler()

fake = Faker('en_US')


# signalR连接类
class SignalRConnection:
	def __init__(self, host="http://192.168.1.59:8201/MISFactory"):
		self.host = host
		self.connection_id = None  # 建立连接时存储连接id
		self.create_group_rec_message = None  # 创建群组返回的消息
		self.add_member_rec_message = None  # 添加成员后返回的消息
		self.synergy_rec_message = None  # 添加成员后返回的消息
		self.other_rec_message = None  # 其他事件返回的消息

	# 获取id的回调函数
	def get_connection_id(self, message):
		self.connection_id = message[0]
		logging.info(self.connection_id)

	# 获取signalR消息
	def get_rec_message(self, message):
		if message[0]['command'] == 'MIS_Create':
			self.create_group_rec_message = message[0]
			logging.info(f"监听到MIS_Create的返回消息:{message}")
		elif message[0]['command'] == 'MIS_AddGroup':
			self.add_member_rec_message = message[0]
			logging.info(f"监听到MIS_AddGroup的返回消息{message}")
		elif message[0]['command'] == 'MIS_Synergy':
			self.synergy_rec_message = message[0]
			logging.info(f"监听到MIS_Synergy的返回消息{message}")
		else:
			self.other_rec_message = message[0]
			logging.info(f"监听到返回消息{message[0]}")

	async def connection_start(self):
		hub_connection = (HubConnectionBuilder()
						  .with_url(self.host)
						  .configure_logging(logging.DEBUG, handler=handler)
						  .with_automatic_reconnect({
			"type": "raw",
			"keep_alive_interval": 10,
			"reconnect_interval": 5,
			"max_attempts": 5}).build())
		try:
			# 连接打开时触发
			hub_connection.on_open(
				lambda: logging.info("连接已打开，握手已接收，准备发送消息..."))
			# 连接关闭时触发
			hub_connection.on_close(lambda: logging.info("连接关闭!"))
			# 监听事件，调用回调函数
			hub_connection.on("ConnectionID", self.get_connection_id)
			hub_connection.on("ReceiveMessage", self.get_rec_message)
			await hub_connection.start()
		except Exception as e:
			logging.error(str(e))

		return hub_connection


# finally:
# 	await self.hub_connection.stop()


# MIS创建群组类
class MISCreateGroup:
	def __init__(self, connection_id):
		self.group_name = f"Group-{random.choice(string.ascii_uppercase)}"  # 随机取房间名称
		self.user_id = str(uuid4())
		self.user_name = fake.name()
		self.create_req_message = {"Command": "MIS_Create",
								   "Data": {"GroupName": self.group_name, "UserName": self.user_name,
											"UserID": self.user_id,
											"StudyList": [
												{"strPatientID": "0000171564", "strAccessionNumber": "11156070",
												 "strModality": "DX",
												 "strStudyInstanceUID": "1.3.51.20211123155502.11156070.359064",
												 "strDicomDiretoryPath": None, "strQueryJsonUri": None}]},
								   "ConnectionID": connection_id}

	# 创建群组
	async def mis_create_group(self, connection, event):
		try:
			await event.wait()
			await connection.invoke("INVOKE", [self.create_req_message])
		except Exception as e:
			logging.error(str(e))


async def main():
	create_event = asyncio.Event()
	sr = SignalRConnection()
	conn_task = await asyncio.create_task(sr.connection_start())

	create_event.set()
	mcg = MISCreateGroup(sr.connection_id)
	mcg_task = await asyncio.create_task(mcg.mis_create_group(conn_task, create_event))

	await asyncio.gather(conn_task, mcg_task)


if __name__ == '__main__':
	asyncio.run(main())
