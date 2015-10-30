# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from datetime import datetime
import common_pb2
from bson.objectid import ObjectId
from pymongo.collection import ReturnDocument
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
import package
from account_valid import user_is_valid_consumer, user_is_valid_merchant
from mongo_connection import get_mongo_collection
from merchant import merchant_exist, merchant_retrieve_with_numbers, user_is_merchant_manager, \
    merchant_retrieve_with_merchant_identity, merchant_material_copy_from_document
from consumer import consumer_retrieve_with_numbers, consumer_material_copy_from_document


class Credit():
    """
    注册登录模块，命令号<100
    request：请求包解析后的pb格式
    """
    def __init__(self, request):
        self.request = request
        self.head = request.head
        self.cmd = self.head.cmd
        self.seq = self.head.seq
        self.numbers = self.head.numbers
        self.code = 1    # 模块号(2位) + 功能号(2位) + 错误号(2位)
        self.message = ""

    def enter(self):
        """
        处理具体业务
        :return: 0/不回包给前端，pb/正确返回，timeout/超时
        """
        # TODO... 验证登录态
        try:
            command_handle = {301: self.consumption_create, 302: self.merchant_credit_retrieve,
                              303: self.confirm_consumption, 304: self.refuse_consumption, 305: self.credit_free}
                              # 304: self.merchant_update, 305: self.merchant_delete, 306: self.merchant_create_manager,
                              # 307: self.merchant_create_manager, 308: self.merchant_delegate_manager,
                              # 309: self.merchant_delete_manager}
            result = command_handle.get(self.cmd, self.dummy_command)()
            if result == 0:
                # 错误或者异常，不回包
                response = 0
            elif result == 1:
                # 错误，且回包
                response = package.error_response(self.cmd, self.seq, self.code, self.message)
            else:
                # 正确，回包
                response = result
            return response
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def consumption_create(self):
        """
        创建用户消费记录
        """
        try:
            body = self.request.consumption_create_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            sums = body.sums

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to create consumption %s", self.numbers, numbers)
                self.code = 40108
                self.message = "no privilege to create consumption"
                return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "sums": sums}
            g_log.debug("create consumption: %s", kwargs)
            self.code, self.message = consumption_create(**kwargs)

            if 40100 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "create consumption done"

                response.consumption_create_response.credit_identity = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def merchant_credit_retrieve(self):
        """
        读取积分详情
        """
        try:
            body = self.request.merchant_credit_retrieve_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to retrieve credit", self.numbers)
                self.code = 40212
                self.message = "no privilege to retrieve credit"
                return 1

            if not merchant_identity:
                g_log.debug("retrieve manager %s all merchant credits", numbers)
                self.code, self.message = merchant_credit_retrieve_with_numbers(numbers)
                pass
            else:
                g_log.debug("retrieve manage %s merchant %s credit", numbers, merchant_identity)
                self.code, self.message = merchant_credit_retrieve_with_merchant_identity(numbers, merchant_identity)

            if 40200 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve credit done"

                # credit = self.message
                merchant_credit = response.merchant_credit_retrieve_response.merchant_credit
                # 遍历管理员所有商家
                for value in self.message:
                    merchant_credit_one = merchant_credit.add()
                    # 商家资料
                    merchant_material_copy_from_document(merchant_credit_one.merchant, value[0])

                    last_customer = ""      # 是否是一个用户的积分
                    aggressive_credit = merchant_credit_one.aggressive_credit
                    for value_credit in value[1]:
                        if last_customer != value_credit["numbers"]:
                            # 新用户的积分
                            aggressive_credit_one = aggressive_credit.add()
                            credit = aggressive_credit_one.credit
                            # 用户资料
                            code, consumer = consumer_retrieve_with_numbers(value_credit["numbers"])
                            if code != 20200:
                                g_log.error("retrieve consumer %s failed", value_credit["numbers"])
                                return 40213, "retrieve consumer failed"
                            consumer_material_copy_from_document(aggressive_credit_one.consumer, consumer)
                            last_customer = value_credit["numbers"]

                        # 用户添加一条积分记录
                        credit_one = credit.add()
                        credit_copy_from_document(credit_one, value_credit)
                        # g_log.debug(credit_one)
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def confirm_consumption(self):
        """
        商家确认消费兑换成积分
        """
        try:
            body = self.request.confirm_consumption_request
            numbers = body.numbers
            manager_numbers = body.manager_numbers
            merchant_identity = body.merchant_identity
            credit_identity = body.credit_identity
            credit = body.credit

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            if not manager_numbers:
                # TODO... 根据包体中的manager_identity获取numbers
                pass

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != manager_numbers:
                g_log.warning("%s is not manager %s", self.numbers, manager_numbers)
                self.code = 40308
                self.message = "no privilege to gift credit"
                return 1

            kwargs = {"numbers": numbers, "credit_identity": credit_identity, "merchant_identity": merchant_identity,
                      "manager": manager_numbers, "credit": credit}
            g_log.debug("confirm consumption: %s", kwargs)
            self.code, self.message = confirm_consumption(**kwargs)

            if 40300 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "confirm consumption done"

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def refuse_consumption(self):
        pass

    def credit_free(self):
        """
        商家赠送积分
        """
        try:
            body = self.request.credit_free_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            credit = body.credit
            manager_numbers = body.manager_numbers

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            if not manager_numbers:
                # TODO... 根据包体中的manager_identity获取numbers
                pass

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != manager_numbers:
                g_log.warning("%s is not manager %s", self.numbers, manager_numbers)
                self.code = 40508
                self.message = "no privilege to gift credit"
                return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity,
                      "manager": manager_numbers, "credit": credit}
            g_log.debug("create consumption: %s", kwargs)
            self.code, self.message = credit_free(**kwargs)

            if 40500 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "gift credit done"

                response.credit_free_response.credit_identity = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    # def enter(self):
    #     """
    #     处理具体业务
    #     :return: 0/不回包给前端，pb/正确返回，timeout/超时
    #     """
    #     if self.cmd == 1:
    #         # 注册
    #
    #         # 模拟旁路
    #         vip = common_pb2.Request()
    #         vip.head.cmd = 1000
    #         vip.head.seq = 10
    #         vip.head.phone_number = self.head.phone_number
    #
    #         response = branch_socket.send_to_branch("vip", vip)
    #         if response == 0:
    #             # 旁路错误逻辑，用户根据业务情况自己决定返回结果
    #             pass
    #         elif response == "timeout":
    #             # 旁路超时逻辑，用户根据业务情况自己决定返回结果
    #             # return "timeout"
    #             # g_log.debug("vip timeoutttttttt")
    #             pass
    #         else:
    #             g_log.debug("branch vip check ok")
    #             # g_log.debug("get response from branch vip")
    #             # g_log.debug("%s", response)
    #
    #         # 返回结果
    #         response = common_pb2.Response()
    #         response.head.cmd = self.head.cmd
    #         response.head.seq = self.head.seq
    #         response.head.code = 1
    #         response.head.message = "register succeed"
    #         g_log.debug("%s", response)
    #         return response
    #     else:
    #         # 错误的命令
    #         return 0

    def dummy_command(self):
        # 无效的命令，不回包
        g_log.debug("unknow command %s", self.cmd)
        return 0


def enter(request):
    """
    积分模块入口
    :param request: 解析后的pb格式
    :return: 0/不回包给前端，pb/正确返回，timeout/超时
    """
    try:
        credit = Credit(request)
        return credit.enter()
    except Exception as e:
        g_log.error("%s", e)
        return 0
    pass


def consumption_create(**kwargs):
    """
    创建用户消费记录
    gift 消费记录/0，赠送积分/1
    :param kwargs: {"numbers": "18688982240", "merchant_identity": "", "sums": 250}
    :return: (40100, credit_identity)/成功，(>40100, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not user_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40101, "invalid phone number"

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.error("lost merchant")
            return 40102, "illegal argument"

        sums = kwargs.get("sums")
        if not sums or sums < 0:
            g_log.error("sums %s illegal", sums)
            return 40103, "illegal argument"

        # 检查商家是否存在
        if not merchant_exist(merchant_identity):
            g_log.error("merchant %s not exit", merchant_identity)
            return 40105, "illegal argument"

        # 用户ID，商户ID，消费金额，消费时间，是否兑换成积分，兑换成多少积分，兑换操作管理员，兑换时间，积分剩余量
        value = {"numbers": numbers, "merchant_identity": merchant_identity, "consumption_time": datetime.now(),
                 "sums": sums, "exchanged": 0, "credit": 0, "manager_numbers": "", "gift": 0,
                 "exchange_time": datetime(1970, 1, 1), "credit_rest": 0}

        collection = get_mongo_collection(numbers, "credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40106, "get collection credit failed"
        credit_identity = collection.insert_one(value).inserted_id
        credit_identity = str(credit_identity)
        g_log.debug("insert consumption %s", value)

        return 40100, credit_identity
    # except (mongo.ConnectionError, mongo.TimeoutError) as e:
    #     g_log.error("connect to mongo failed")
    #     return 30102, "connect to mongo failed"
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40107, "exception"


def merchant_credit_retrieve_with_numbers(numbers):
    """
    获取管理员所有积分详情
    :param numbers: 管理员号码
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        if not user_is_valid_merchant(numbers):
            g_log.warning("invalid merchant manager %s", numbers)
            return 40201, "invalid merchant manager"

        code, merchants = merchant_retrieve_with_numbers(numbers)
        if code != 30200:
            g_log.debug("retrieve merchant material of manager %s failed", numbers)
            return 40202, "retrieve merchant material failed"

        merchant_credit = []
        for merchant in merchants:
            # TODO... 广播查询所有积分
            # TODO...待数据层独立时处理，目前只考虑单机，逻辑层数据层合并
            collection = get_mongo_collection("", "credit")
            if not collection:
                g_log.error("get collection credit failed")
                return 40203, "get collection credit failed"
            credit = collection.find({"merchant_identity": merchant["merchant_identity"]},
                                     {"merchant_identity": False}).sort("numbers")
            g_log.debug("merchant has %s credit", credit.count())
            merchant_credit.append((merchant, credit))
        return 40200, merchant_credit
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40204, "exception"


def merchant_credit_retrieve_with_identity(identity):
    """
    获取管理员所有积分详情
    :param identity: 管理员ID
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        # 根据商家id查找商家电话号码
        numbers = ""
        return merchant_credit_retrieve_with_numbers(numbers)
    except Exception as e:
        g_log.error("%s", e)
        return 40205, "exception"


def merchant_credit_retrieve(numbers=None, identity=None):
    """
    获取管理员所有积分详情，商家电话号码优先
    :param numbers: 商家管理员电话号码
    :param identity: 商家管理员ID
    :return:(40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        if numbers:
            return merchant_credit_retrieve_with_numbers(numbers)
        elif identity:
            return merchant_credit_retrieve_with_identity(identity)
        else:
            return 40206, "bad arguments"
    except Exception as e:
        g_log.error("%s", e)
        return 40207, "exception"


def merchant_credit_retrieve_with_merchant_identity(numbers, merchant_identity):
    """
    获取管理员指定商家积分详情
    :param numbers: 管理员账号
    :param merchant_identity: 商家ID
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        if not user_is_valid_merchant(numbers):
            g_log.warning("invalid merchant manager %s", numbers)
            return 40208, "invalid merchant manager"

        code, merchant_material = merchant_retrieve_with_merchant_identity(numbers, merchant_identity)
        if code != 30200:
            g_log.debug("retrieve merchant %s material failed", merchant_identity)
            return 40209, "retrieve merchant material failed"

        # TODO... 广播查询所有积分
        # TODO...待数据层独立时处理，目前只考虑单机，逻辑层数据层合并
        collection = get_mongo_collection("", "credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40210, "get collection credit failed"
        credit = collection.find({"merchant_identity": merchant_identity}, {"merchant_identity": False}).sort("numbers")
        g_log.debug("merchant has %s credit", credit.count())
        # for credit in credit:
        #     g_log.debug(credit)
        return 40200, [(merchant_material[0], credit)]
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40211, "exception"


def confirm_consumption(**kwargs):
    """
    商家确认消费兑换成积分
    :param kwargs: {"numbers": "18688982240", "credit_identity": "", "manager": "118688982241", "credit": 350}
    :return:
    """
    try:
        numbers = kwargs.get("numbers", "")
        if not user_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40301, "invalid customer"

        manager = kwargs.get("manager", "")
        if not user_is_valid_merchant(manager):
            g_log.warning("invalid manager %s", manager)
            return 40302, "invalid manager"

        credit_identity = kwargs.get("credit_identity")
        if not credit_identity:
            g_log.warning("no credit identity")
            return 40303, "illegal argument"
        credit_identity = ObjectId(credit_identity)

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.warning("no merchant identity")
            return 40304, "illegal argument"

        # 检查商家管理员
        if not user_is_merchant_manager(manager, merchant_identity):
            g_log.error("manager %s is not merchant %s manager", manager, merchant_identity)
            return 40308, "manager is not merchant manager"

        credit = kwargs.get("credit")
        if not credit:
            g_log.info("no credit argument")
            # TODO... 平台根据兑换比例计算
        else:
            # TODO... 检查credit是否符合兑换比例
            pass

        collection = get_mongo_collection(numbers, "credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40305, "get collection credit failed"

        credit = collection.find_one_and_update({"numbers": numbers, "_id": credit_identity, "exchanged": 0,
                                                 "gift": 0, "merchant_identity": merchant_identity},
                                                {"$set": {"exchanged": 1, "manager_numbers": manager, "credit": credit,
                                                          "exchange_time": datetime.now(), "credit_rest": credit}},
                                                return_document=ReturnDocument.AFTER)
        g_log.debug(credit)
        if not credit or not credit["exchanged"]:
            g_log.error("confirm consumption failed")
            return 40306, "confirm consumption failed"

        return 40300, "yes"
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40307, "exception"


def credit_free(**kwargs):
    """
    商家赠送积分
    gift 消费记录/0，赠送积分/1
    :param kwargs: {"numbers": "18688982240", "merchant_identity": "", "manager": "118688982241", "credit": 350}
    :return: (40500, credit_identity)/成功，(>40500, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not user_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40501, "invalid phone number"

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.error("lost merchant")
            return 40502, "illegal argument"

        credit = kwargs.get("credit")
        if not credit or credit < 0:
            g_log.error("credit %s illegal", credit)
            return 40503, "illegal argument"

        # 检查商家是否存在，TODO... user_is_merchant_manager包含该检查
        if not merchant_exist(merchant_identity):
            g_log.error("merchant %s not exit", merchant_identity)
            return 40504, "illegal argument"

        # 检查是否商家管理员
        manager = kwargs.get("manager")
        if not user_is_valid_merchant(manager):
            g_log.error("manager %s is illegal", manager)
            return 40505, "illegal manager"
        if not user_is_merchant_manager(manager, merchant_identity):
            g_log.error("user %s is not merchant %s manager", manager, merchant_identity)
            return 40506, "not manager"

        # 用户ID，商户ID，消费金额，消费时间，是否兑换成积分，兑换成多少积分，兑换操作管理员，兑换时间，积分剩余量
        value = {"numbers": numbers, "merchant_identity": merchant_identity, "consumption_time": datetime(1970, 1, 1),
                 "sums": 0, "exchanged": 1, "credit": credit, "manager_numbers": manager, "gift": 1,
                 "exchange_time": datetime.now(), "credit_rest": 0}

        collection = get_mongo_collection(numbers, "credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40507, "get collection credit failed"
        credit_identity = collection.insert_one(value).inserted_id
        credit_identity = str(credit_identity)
        g_log.debug("insert consumption %s", value)

        return 40500, credit_identity
    # except (mongo.ConnectionError, mongo.TimeoutError) as e:
    #     g_log.error("connect to mongo failed")
    #     return 30102, "connect to mongo failed"
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40508, "exception"


def credit_copy_from_document(material, value):
    """
    mongo中的单条积分记录赋值给CreditMaterial
    :param material: CreditMaterial
    :param value: 单个积分document
    :return:
    """
    material.gift = value["gift"]
    material.sums = value["sums"]

    material.consumption_time = value["consumption_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.exchanged = value["exchanged"]
    material.credit = value["credit"]
    material.manager_numbers = value["manager_numbers"]
    material.exchange_time = value["exchange_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.credit_rest = value["credit_rest"]

    material.identity = str(value["_id"])
    # material.numbers = value["numbers"]