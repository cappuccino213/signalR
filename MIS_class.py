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
		self.hub_connection = (HubConnectionBuilder()
							   .with_url(self.host)
							   .configure_logging(logging.DEBUG, handler=handler)
							   .with_automatic_reconnect({
			"type": "raw",
			"keep_alive_interval": 10,
			"reconnect_interval": 5,
			"max_attempts": 5}).build())

	connection_id = None

	# 获取连接id
	def get_connection_id(self, message):
		self.connection_id = message[0]
		logging.info(message[0])

	# 获取signalR消息
	# def get_recv_message(self, message):
	#     self.recv_message = message
	#     logging.info(f"接收的消息{message}")

	async def connection_start(self):
		try:
			# 连接打开时触发
			self.hub_connection.on_open(
				lambda: logging.info("connection opened and handshake received ready to send messages"))
			# 连接关闭时触发
			self.hub_connection.on_close(lambda: logging.info("connection closed"))
			# 接受消息,参数是事件、回调函数
			self.hub_connection.on("ConnectionID", self.get_connection_id)
			await self.hub_connection.start()
		except Exception as e:
			logging.error(str(e))

# finally:
#     await self.hub_connection.stop()


# MIS创建群组类
class MISCreateGroup(SignalRConnection):
	def __init__(self):
		super().__init__()
		self.GroupName = f"Group#{random.choice(string.ascii_uppercase)}"  # 随机取房间名称
		self.UserID = str(uuid4())
		self.UserName = fake.name()
		self.create_req_message = {"Command": "MIS_Create",
								   "Data": {"GroupName": self.GroupName, "UserName": self.UserName,
											"UserID": self.UserID,
											"StudyList": [
												{"strPatientID": "0000171564", "strAccessionNumber": "11156070",
												 "strModality": "DX",
												 "strStudyInstanceUID": "1.3.51.20211123155502.11156070.359064",
												 "strDicomDiretoryPath": None, "strQueryJsonUri": None}]},
								   "ConnectionID": self.connection_id}
		self.create_recv_message = None

	group_data = None

	# # 创建群组信息
	def create_group_send_message(self):
		return {"Command": "MIS_Create",
				"Data": {"GroupName": self.GroupName, "UserName": self.UserName, "UserID": self.UserID,
						 "StudyList": [{"strPatientID": "0000171564", "strAccessionNumber": "11156070",
										"strModality": "DX",
										"strStudyInstanceUID": "1.3.51.20211123155502.11156070.359064",
										"strDicomDiretoryPath": None, "strQueryJsonUri": None}]},
				"ConnectionID": self.connection_id}

	# 获取signalR消息
	def get_recv_message(self, message):
		if message[0]['data']['code'] == '1':
			self.create_recv_message = message
			logging.info(f"操作成功{message}")
		else:
			logging.info(f"操作失败{message}")

	# 创建房间
	async def mis_create_group(self):
		try:
			self.hub_connection.on("ReceiveMessage", self.get_recv_message)
			await self.connection_start()
			# await super(MISCreateGroup, self).connection_start()
			# 判断是否接已接收到connectionID，否则不发送信息
			# while not self.connection_id:
			# 	time.sleep(1)
			# 	logging.info("暂未接收到connection_id,继续等待....")
			await self.hub_connection.invoke("INVOKE", [self.create_req_message])
		# self.group_data = self.create_recv_message[0]['data']
		# logging.info(f"解析得到群组信息{self.group_data}")
		except Exception as e:
			logging.error(str(e))


# MIS增加成员类
class MISAddGroup(MISCreateGroup):
	def __init__(self):
		super().__init__()
		self.group_id = self.group_data['data']['groupID']
		self.group_name = self.group_data['data']['groupName']
		self.user_id = str(uuid4())
		self.user_name = fake.name()
		self.add_req_message = {"Command": "MIS_AddGroup",
								"Data": {"GroupID": self.group_id, "GroupName": self.group_name, "UserID": self.user_id,
										 "UserName": self.user_name}, "ConnectionID": self.connection_id}


# MIS消息通信类

if __name__ == '__main__':
	# sr = SignalRConnection()
	# asyncio.run(sr.connection_start())

	mcg = MISCreateGroup()
	asyncio.run(mcg.mis_create_group())
