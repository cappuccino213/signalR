"""
@File : MIS_function.py
@Date : 2022/4/26 9:47
@Author: 九层风（YePing Zhang）
@Contact : yeahcheung213@163.com
"""
import logging
import asyncio
import random
import string
import time

from uuid import uuid4
from faker import Faker

from signalrcore_async.hub_connection_builder import HubConnectionBuilder

URL = 'http://192.168.1.59:8201/MISFactory'

Viewer = 'http://192.168.1.59:8103/imageView'

# 声明日志格式
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
handler = logging.StreamHandler()

fake = Faker('en_US')

connection_id = ''
# 创建群组的监听消息
create_group_rec = {}

# 添加群成员监听消息
add_member_rec = {}

# 协同操作
synergy_rec = {}


# signalR连接
async def signalr_connection(url):
	# 获取连接id
	def get_connection_id(message):
		global connection_id
		connection_id = message[0]
		logging.info(connection_id)

	# 获取signalR消息
	def get_rec_message(message):
		if message[0]['command'] == 'MIS_Create':
			global create_group_rec
			create_group_rec = message[0]
			logging.info(f"监听到MIS_Create的消息已赋值给create_group_rec{message}")
		elif message[0]['command'] == 'MIS_AddGroup':
			global add_member_rec
			add_member_rec = message[0]
			logging.info(f"监听到MIS_AddGroup的消息已赋值给add_member_message{message}")
		elif message[0]['command'] == 'MIS_Synergy':
			global synergy_rec
			synergy_rec = message[0]
			logging.info(f"监听到MIS_Synergy的消息已赋值给synergy_rec{message}")
		else:
			logging.info(f"监听到消息{message[0]}")

	hub_connection = (HubConnectionBuilder()
					  .with_url(url)
					  .configure_logging(logging.DEBUG, handler=handler)
					  .with_automatic_reconnect({
		"type": "raw",
		"keep_alive_interval": 10,
		"reconnect_interval": 5,
		"max_attempts": 5}).build())

	try:
		# 连接打开时触发
		hub_connection.on_open(
			lambda: logging.info("connection opened and handshake received ready to send messages"))
		# 连接关闭时触发
		hub_connection.on_close(lambda: logging.info("connection closed"))
		# 接听接收消息,参数是事件、回调函数
		hub_connection.on("ConnectionID", get_connection_id)
		hub_connection.on("ReceiveMessage", get_rec_message)
		await hub_connection.start()
	except Exception as e:
		logging.error(str(e))
	return hub_connection


# MIS创建群组
async def mis_create_group(connection):
	group_name = f"Group-{random.choice(string.ascii_uppercase)}"  # 随机取房间名称
	user_id = str(uuid4())
	user_name = fake.name()
	message = {"Command": "MIS_Create",
			   "Data": {"GroupName": group_name, "UserName": user_name, "UserID": user_id,
						"StudyList": [{"strPatientID": "CR20211229-00024CR", "strAccessionNumber": "101",
									   "strModality": "CR",
									   "strStudyInstanceUID": "1.2.86.76547135.7.11440624.202191013480",
									   "strDicomDiretoryPath": None, "strQueryJsonUri": None}]},
			   "ConnectionID": connection_id}
	await connection.invoke("INVOKE", [message])
	logging.info(
		f"分享的影像群组url:{Viewer}?strPatientID=CR20211229-00024CR&strAccessionNumber=101&strModality=CR&strStudyInstanceUID=1.2.86.76547135.7.11440624.202191013480&GroupName={group_name}&GroupID={create_group_rec['data']['groupID']}")


# MIS添加群员
async def mis_add_member(connection):
	group_id = create_group_rec['data']['groupID']
	group_name = create_group_rec['data']['groupName']
	user_id = str(uuid4())
	user_name = fake.name()
	message = {"Command": "MIS_AddGroup",
			   "Data": {"GroupID": group_id, "GroupName": group_name, "UserID": user_id,
						"UserName": user_name}, "ConnectionID": connection_id}

	await connection.invoke("INVOKE", [message])


"""业务逻辑"""


async def main():
	conn_task = asyncio.create_task(signalr_connection(URL))

	create_conn = await conn_task

	create_task = asyncio.create_task(mis_create_group(create_conn))

	await create_task

	task_list = []
	for i in range(10):
		add_conn = await asyncio.create_task(signalr_connection(URL))
		add_task = asyncio.create_task(mis_add_member(add_conn))
		task_list.append(add_task)

	await asyncio.gather(*task_list)


if __name__ == "__main__":
	"""协程调用参考https://docs.python.org/zh-cn/3/library/asyncio-task.html"""
	# asyncio.run(signalr_connection(URL))
	# asyncio.run(mis_create_group())
	# asyncio.run(mis_add_member())
	asyncio.run(main())
