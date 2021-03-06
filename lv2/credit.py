# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from datetime import datetime
from date_auxiliary import after_weeks, after_years
import common_pb2
from bson.objectid import ObjectId
from pymongo.collection import ReturnDocument
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
import package
from account_valid import account_is_valid_consumer, account_is_valid_merchant
from account_auxiliary import identity_to_numbers, verify_session_key
from mongo_connection import get_mongo_collection
from merchant import merchant_exist, merchant_retrieve_with_numbers, user_is_merchant_manager, \
    merchant_retrieve_with_merchant_identity, merchant_material_copy_from_document, \
    merchant_retrieve_with_merchant_identity_only, merchant_material_copy_from_document_base
from consumer import consumer_retrieve_with_numbers, consumer_material_copy_from_document
from business import consumption_to_credit, credit_conversion
from flow_auxiliary import credit_exceed_upper, balance_overdraft
from flow import merchant_credit_update, merchant_credit_update_batch


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
        self.session_key = self.head.session_key

        self.code = 1    # 模块号(2位) + 功能号(2位) + 错误号(2位)
        self.message = ""

    def enter(self):
        """
        处理具体业务
        :return: 0/不回包给前端，pb/正确返回，timeout/超时
        """
        try:
            # 验证登录态，某些命令可能不需要登录态，此处做判断
            code, message = verify_session_key(self.numbers, self.session_key)
            if 10400 != code:
                g_log.debug("verify session key failed, %s, %s", code, message)
                return package.error_response(self.cmd, self.seq, 40001, "invalid session key")

            command_handle = {301: self.consumption_create, 302: self.merchant_credit_retrieve,
                              303: self.confirm_consumption, 304: self.refuse_consumption,
                              305: self.credit_free, 306: self.consumer_credit_retrieve,
                              307: self.consume_credit, 308: self.consume_credit_retrieve,
                              309: self.credit_interchange, 310: self.credit_interchange_retrieve,
                              311: self.check_interchange_in, 312: self.allow_out_credit_retrieve}
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
            identity = body.identity
            merchant_identity = body.merchant_identity
            sums = body.sums

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 40101
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to create consumption %s", self.numbers, numbers)
                self.code = 40102
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
            identity = body.identity
            merchant_identity = body.merchant_identity
            consumer_numbers = body.consumer_numbers

            if not numbers:
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 40201
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to retrieve credit", self.numbers)
                self.code = 40202
                self.message = "no privilege to retrieve credit"
                return 1

            if not merchant_identity:
                g_log.debug("retrieve manager %s all merchant credits", numbers)
                self.code, self.message = merchant_credit_retrieve_with_numbers(numbers)
            else:
                if consumer_numbers:
                    g_log.debug("retrieve manage %s merchant %s of %s credit", numbers, merchant_identity,
                                consumer_numbers)
                    self.code, self.message = merchant_credit_retrieve_with_merchant_identity(
                        numbers, merchant_identity, consumer_numbers)
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
                    g_log.debug(value)
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
                                return 40203, "retrieve consumer failed"
                            consumer_material_copy_from_document(aggressive_credit_one.consumer, consumer)
                            last_customer = value_credit["numbers"]

                        # 用户添加一条积分记录
                        credit_one = credit.add()
                        credit_copy_from_document_base(credit_one, value_credit)
                        # credit_copy_from_document(credit_one, value_credit)
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
            identity = body.identity
            merchant_identity = body.merchant_identity
            credit_identity = body.credit_identity
            sums = body.sums

            if not numbers:
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 40301
                    self.message = "missing argument"
                    return 1

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 40302
                self.message = "no privilege to gift credit"
                return 1

            kwargs = {"numbers": numbers, "credit_identity": credit_identity, "merchant_identity": merchant_identity,
                      "sums": sums}
            g_log.debug("confirm consumption: %s", kwargs)
            self.code, self.message = confirm_consumption(**kwargs)

            if 40300 == self.code:
                # 确认成功
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
        """
        商家拒绝消费兑换成积分
        """
        try:
            body = self.request.refuse_consumption_request
            numbers = body.numbers
            identity = body.identity
            merchant_identity = body.merchant_identity
            credit_identity = body.credit_identity
            reason = body.reason

            if not numbers:
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 40401
                    self.message = "missing argument"
                    return 1

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 40408
                self.message = "no privilege to gift credit"
                return 1

            kwargs = {"numbers": numbers, "credit_identity": credit_identity, "merchant_identity": merchant_identity,
                      "reason": reason}
            g_log.debug("refuse consumption: %s", kwargs)
            self.code, self.message = refuse_consumption(**kwargs)

            if 40400 == self.code:
                # 成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "refuse consumption done"

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

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

    def consumer_credit_retrieve(self):
        """
        用户查询拥有的所有积分
        """
        try:
            body = self.request.consumer_credit_retrieve_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to retrieve credit %s", self.numbers, numbers)
                self.code = 40605
                self.message = "no privilege to retrieve credit"
                return 1

            # kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "sums": sums}
            g_log.debug("retrieve credit: %s", numbers)
            self.code, self.message = consumer_credit_retrieve(numbers, merchant_identity)

            if 40600 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve credit done"

                value = self.message
                consumer_credit = response.consumer_credit_retrieve_response.consumer_credit

                # 用户资料
                consumer_material_copy_from_document(consumer_credit.consumer, value[0])
                # 遍历用户所有积分
                last_merchant = ""
                aggressive_credit = consumer_credit.aggressive_credit
                for value_credit in value[1]:
                    if last_merchant != value_credit["merchant_identity"]:
                        # 新用户的积分
                        aggressive_credit_one = aggressive_credit.add()
                        credit = aggressive_credit_one.credit
                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value_credit["merchant_identity"])
                        if code != 30200:
                            g_log.error("retrieve merchant %s failed", value_credit["merchant_identity"])
                            return 40605, "retrieve merchant failed"
                        merchant_material_copy_from_document_base(aggressive_credit_one.merchant, merchants[0])
                        # merchant_material_copy_from_document(aggressive_credit_one.merchant, merchants[0])
                        last_merchant = value_credit["merchant_identity"]

                    # 用户添加一条积分记录
                    credit_one = credit.add()
                    credit_copy_from_document_base(credit_one, value_credit)
                    # credit_copy_from_document(credit_one, value_credit)
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            from print_exception import print_exception
            print_exception()
            return 0

    def consume_credit(self):
        """
        积分消费
        """
        try:
            body = self.request.consume_credit_request
            numbers = body.numbers
            credit_identity = body.credit_identity
            # merchant_identity = body.merchant_identity
            credit = body.credit

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 40709
                self.message = "no privilege to consume credit"
                return 1

            kwargs = {"numbers": numbers, "credit_identity": credit_identity, "credit": credit}
            g_log.debug("consume credit: %s", kwargs)
            self.code, self.message = consume_credit(**kwargs)

            if 40700 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "consume credit done"

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def consume_credit_retrieve(self):
        """
        积分消费记录查询
        """
        try:
            body = self.request.consume_credit_retrieve_request
            numbers = body.numbers
            begin_time = body.begin_time
            end_time = body.end_time
            limit = body.limit

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 40804
                self.message = "no privilege to consume credit"
                return 1

            kwargs = {"numbers": numbers, "begin_time": begin_time, "end_time": end_time, "limit": limit}
            g_log.debug("consume credit: %s", kwargs)
            self.code, self.message = consume_credit_retrieve(**kwargs)

            if 40800 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "consume credit done"

                consume_record = response.consume_credit_retrieve_response.consume_record
                last_merchant = ""      # 是否是一个用户的积分
                # 遍历管理员所有商家
                for value in self.message:
                    if last_merchant != value["merchant_identity"]:
                        consume_record_one = consume_record.add()
                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value["merchant_identity"])
                        merchant_material_copy_from_document(consume_record_one.merchant, merchants[0])
                        consume = consume_record_one.consume
                    consume_one = consume.add()
                    last_merchant = value["merchant_identity"]
                    consume_copy_from_document(consume_one, value)

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def credit_interchange(self):
        """
        积分兑换
        """
        try:
            body = self.request.credit_interchange_request
            numbers = body.numbers
            identity = body.identity
            credit_identity = body.credit_identity
            from_merchant = body.from_merchant
            to_merchant = body.to_merchant
            credit = body.credit
            exec_interchange = body.exec_interchange

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 40901
                    self.message = "missing argument"
                    return 1

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 40902
                self.message = "no privilege to consume credit"
                return 1

            kwargs = {"numbers": numbers, "credit_identity": credit_identity, "to_merchant": to_merchant,
                      "from_merchant": from_merchant, "credit": credit, "exec_interchange": exec_interchange}
            g_log.debug("interchange credit: %s", kwargs)
            self.code, self.message = credit_interchange(**kwargs)

            if 40900 == self.code:
                # 成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "consume credit done"

                response.credit_interchange_response.credit = self.message[0]
                response.credit_interchange_response.fee = self.message[1]
                return response
            else:
                return 1
        except Exception as e:
            # from print_exception import print_exception
            # print_exception()
            g_log.error("%s", e)
            return 0

    def credit_interchange_retrieve(self):
        """
        积分兑记录查询
        """
        try:
            body = self.request.credit_exchange_retrieve_request
            numbers = body.numbers
            begin_time = body.begin_time
            end_time = body.end_time
            limit = body.limit

            if not numbers:
                # TODO... 根据包体中的identity获取numbers
                pass

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 41004
                self.message = "no privilege to exchange record"
                return 1

            kwargs = {"numbers": numbers, "begin_time": begin_time, "end_time": end_time, "limit": limit}
            g_log.debug("exchange record: %s", kwargs)
            self.code, self.message = credit_interchange_retrieve(**kwargs)

            if 41000 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve exchange record done"

                exchange_record = response.credit_exchange_retrieve_response.exchange_record
                last_merchant = [("", "")]      # 是否是一个用户的积分
                # 遍历管理员所有商家
                for value in self.message:
                    if last_merchant[0] != (value["from_merchant"], value["to_merchant"]):
                        exchange_record_one = exchange_record.add()
                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value["from_merchant"])
                        merchant_material_copy_from_document(exchange_record_one.from_merchant, merchants[0])
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value["to_merchant"])
                        merchant_material_copy_from_document(exchange_record_one.to_merchant, merchants[0])
                        exchange = exchange_record_one.exchange
                    exchange_one = exchange.add()
                    last_merchant[0] = (value["from_merchant"], value["to_merchant"])
                    interchange_copy_from_document(exchange_one, value)

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def check_interchange_in(self):
        """
        积分兑记录查询
        """
        try:
            body = self.request.allow_interchange_in_request
            numbers = body.numbers
            identity = body.identity
            merchant = body.merchant

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 41101
                    self.message = "missing argument"
                    return 1

            # 发起请求的操作员和商家管理员不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s is not manager %s", self.numbers, numbers)
                self.code = 41102
                self.message = "no privilege to exchange record"
                return 1

            self.code, self.message = credit_exceed_upper(**{"merchant_identity": merchant, "allow_last": "yes"})
            if 61000 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "check exchange in done"

                body = response.allow_interchange_in_response
                body.allow = "yes" if bool(self.message) else "no"

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def allow_out_credit_retrieve(self):
        """
        用户查询拥有的所有允许导出的积分
        """
        try:
            body = self.request.allow_out_credit_retrieve_request
            numbers = body.numbers
            identity = body.identity
            merchant_identity = body.merchant_identity

            if not numbers:
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 41201
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要创建的消费记录用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to retrieve credit %s", self.numbers, numbers)
                self.code = 41202
                self.message = "no privilege to retrieve credit"
                return 1

            # kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "sums": sums}
            g_log.debug("retrieve credit: %s", numbers)
            self.code, self.message = consumer_credit_retrieve(numbers, merchant_identity)

            if 40600 == self.code:
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve credit done"

                value = self.message
                consumer_credit = response.allow_out_credit_retrieve_response.consumer_credit

                # 用户资料
                consumer_material_copy_from_document(consumer_credit.consumer, value[0])
                # 遍历用户所有积分
                last_merchant = ""
                aggressive_credit = consumer_credit.aggressive_credit
                for value_credit in value[1]:
                    if last_merchant != value_credit["merchant_identity"]:
                        # 检查商家积分允许被换出
                        code, overdraft = balance_overdraft(value_credit["merchant_identity"])
                        g_log.debug("%s,%s", value_credit["merchant_identity"], overdraft)
                        if overdraft != "yes":
                            # last_merchant = value_credit["merchant_identity"]
                            continue

                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value_credit["merchant_identity"])
                        if code != 30200:
                            g_log.error("retrieve merchant %s failed", value_credit["merchant_identity"])
                            return 41205, "retrieve merchant failed"

                        # 新用户的积分
                        aggressive_credit_one = aggressive_credit.add()
                        credit = aggressive_credit_one.credit

                        merchant_material_copy_from_document(aggressive_credit_one.merchant, merchants[0])
                        last_merchant = value_credit["merchant_identity"]

                    # 用户添加一条积分记录
                    credit_one = credit.add()
                    credit_copy_from_document(credit_one, value_credit)
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            from print_exception import print_exception
            print_exception()
            return 0

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
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40111, "invalid phone number"

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.error("lost merchant")
            return 40112, "illegal argument"

        sums = kwargs.get("sums")
        if not sums or sums < 0:
            g_log.error("sums %s illegal", sums)
            return 40113, "illegal argument"

        # 检查商家是否存在
        if not merchant_exist(merchant_identity):
            g_log.error("merchant %s not exit", merchant_identity)
            return 40115, "illegal argument"

        # 用户ID，商户ID，消费金额，消费时间，是否兑换成积分，兑换成多少积分，兑换操作管理员，兑换时间，积分剩余量
        value = {"numbers": numbers, "merchant_identity": merchant_identity, "consumption_time": datetime.now(),
                 "sums": sums, "exchanged": 0, "credit": 0, "manager_numbers": "", "type": "c",
                 "exchange_time": datetime(1970, 1, 1), "expire_time": after_weeks(1), "credit_rest": 0}

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40116, "get collection credit failed"
        credit_identity = collection.insert_one(value).inserted_id
        credit_identity = str(credit_identity)
        g_log.debug("insert consumption %s", value)

        return 40100, credit_identity
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40117, "exception"


def merchant_credit_retrieve_with_numbers(numbers):
    """
    获取管理员所有积分详情
    :param numbers: 管理员号码
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        if not account_is_valid_merchant(numbers):
            g_log.warning("invalid merchant manager %s", numbers)
            return 40211, "invalid merchant manager"

        code, merchants = merchant_retrieve_with_numbers(numbers)
        if code != 30200:
            g_log.debug("retrieve merchant material of manager %s failed", numbers)
            return 40212, "retrieve merchant material failed"

        merchant_credit = []
        for merchant in merchants:
            collection = get_mongo_collection("credit")
            if not collection:
                g_log.error("get collection credit failed")
                return 40213, "get collection credit failed"
            merchant_identity = str(merchant["_id"])
            g_log.debug(merchant_identity)
            credit = collection.find({"merchant_identity": merchant_identity, "expire_time": {"$gte": datetime.now()},
                                      "type": {"$ne": "r"}}, {"merchant_identity": False}).sort("numbers")

            g_log.debug("merchant has %s credit", credit.count())
            merchant_credit.append((merchant, credit))
        return 40200, merchant_credit
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40214, "exception"


def merchant_credit_retrieve_with_identity(identity):
    """
    获取管理员所有积分详情
    :param identity: 管理员ID
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        # 根据商家id查找商家电话号码
        code, numbers = identity_to_numbers(identity)
        if code != 10500:
            return 40215, "illegal identity"
        return merchant_credit_retrieve_with_numbers(numbers)
    except Exception as e:
        g_log.error("%s", e)
        return 40216, "exception"


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
            return 40217, "bad arguments"
    except Exception as e:
        g_log.error("%s", e)
        return 40218, "exception"


def merchant_credit_retrieve_with_merchant_identity(numbers, merchant_identity, consumer_numbers=""):
    """
    获取管理员指定商家积分详情
    :param numbers: 管理员账号
    :param merchant_identity: 商家ID
    :return: (40200, [(merchant, credit),...])/成功，(>40200, "errmsg")/失败
    """
    try:
        if not account_is_valid_merchant(numbers):
            g_log.warning("invalid merchant manager %s", numbers)
            return 40219, "invalid merchant manager"

        code, merchant_material = merchant_retrieve_with_merchant_identity(numbers, merchant_identity)
        if code != 30200:
            g_log.debug("retrieve merchant %s material failed", merchant_identity)
            return 40220, "retrieve merchant material failed"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40221, "get collection credit failed"
        if consumer_numbers:
            credit = collection.find({"merchant_identity": merchant_identity, "numbers": consumer_numbers,
                                      "type": {"$ne": "r"}, "expire_time": {"$gte": datetime.now()}},
                                     {"merchant_identity": False}).sort("exchange_time")
        else:
            credit = collection.find({"merchant_identity": merchant_identity, "expire_time": {"$gte": datetime.now()},
                                      "type": {"$ne": "r"}}, {"merchant_identity": False}).sort("numbers")
        g_log.debug("merchant has %s credit", credit.count())

        return 40200, [(merchant_material[0], credit)]
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40222, "exception"


def confirm_consumption(**kwargs):
    """
    商家确认消费兑换成积分
    :param kwargs: {"numbers": "18688982240", "credit_identity": "", "manager": "118688982241", "sums": sums}
    :return:
    """
    try:
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40311, "invalid customer"

        credit_identity = kwargs.get("credit_identity")
        if not credit_identity:
            g_log.warning("no credit identity")
            return 40313, "illegal argument"
        credit_identity = ObjectId(credit_identity)

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.warning("no merchant identity")
            return 40314, "illegal argument"

        sums = kwargs.get("sums")
        if sums < 0:
            g_log.warning("illegal sums")
            return 40315, "illegal argument"
        # 检查商家管理员
        if not user_is_merchant_manager(numbers, merchant_identity):
            g_log.error("manager %s is not merchant %s manager", numbers, merchant_identity)
            return 40316, "manager is not merchant manager"

        # TODO... 平台根据兑换比例计算，判断是已发行积分否已经超过最大可发行量
        code, message = consumption_to_credit(merchant_identity, sums)
        if code != 51000:
            g_log.error("calculus money to credit failed, %s", message)
            return 40317, "calculus money to credit failed"
        else:
            credit = int(message)
            if credit == 0:
                # 至少有一个积分
                credit = 1

        code, message = credit_exceed_upper(**{"merchant_identity": merchant_identity, "credit": credit})
        if code == 61000:
            if not bool(message):
                g_log.debug("apply credit exceed upper bound")
                return 40322, "apply credit exceed upper bound"
            g_log.debug("apply credit allow")
        else:
            g_log.debug("apply not allowed")
            return 40323, "check upper bound failed"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40318, "get collection credit failed"

        result = collection.find_one_and_update({"_id": credit_identity, "exchanged": 0, "sums": sums,
                                                 "merchant_identity": merchant_identity},
                                                {"$set": {"exchanged": 1, "manager_numbers": numbers, "credit": credit,
                                                          "exchange_time": datetime.now(), "credit_rest": credit,
                                                          "expire_time": after_years(1)}},
                                                return_document=ReturnDocument.AFTER)
        g_log.debug(result)
        if not result or not result["exchanged"]:
            g_log.error("confirm consumption failed")
            return 40319, "confirm consumption failed"

        # 更新已发行积分量(用户消费从商家获得的积分)
        code, message = merchant_credit_update(**{"numbers": numbers, "merchant_identity": merchant_identity,
                                                  "mode": "issued", "supplement": credit})
        if code != 60400:
            g_log.error("update issued credit failed")
            return 40321, "update issued credit failed"

        return 40300, "yes"
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40320, "exception"


def refuse_consumption(**kwargs):
    """
    商家确认消费兑换成积分
    :param kwargs: {"numbers": "18688982240", "credit_identity": "", "manager": "118688982241", "reason": "xxxx"}
    :return:
    """
    try:
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40411, "invalid customer"

        reason = kwargs.get("reason", "")
        if len(reason) > 16:
            g_log.warning("too long introduce %s", reason)
            reason = reason[0:16]

        credit_identity = kwargs.get("credit_identity")
        if not credit_identity:
            g_log.warning("no credit identity")
            return 40413, "illegal argument"
        credit_identity = ObjectId(credit_identity)

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.warning("no merchant identity")
            return 40414, "illegal argument"

        # 检查商家管理员
        if not user_is_merchant_manager(numbers, merchant_identity):
            g_log.error("manager %s is not merchant %s manager", numbers, merchant_identity)
            return 40415, "manager is not merchant manager"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40416, "get collection credit failed"
        credit = collection.find_one_and_update({"_id": credit_identity, "exchanged": 0,
                                                 "merchant_identity": merchant_identity},
                                                {"$set": {"manager_numbers": numbers, "reason": reason,
                                                          "exchange_time": datetime.now(), "type": "r"}},
                                                return_document=ReturnDocument.AFTER)
        # g_log.debug(credit)
        if not credit:
            g_log.error("refuse consumption failed")
            return 40417, "refuse consumption failed"

        return 40400, "yes"
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40418, "exception"


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
        if not account_is_valid_consumer(numbers):
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
        if not account_is_valid_merchant(manager):
            g_log.error("manager %s is illegal", manager)
            return 40505, "illegal manager"
        if not user_is_merchant_manager(manager, merchant_identity):
            g_log.error("user %s is not merchant %s manager", manager, merchant_identity)
            return 40506, "not manager"

        # 用户ID，商户ID，消费金额，消费时间，是否兑换成积分，兑换成多少积分，兑换操作管理员，兑换时间，积分剩余量
        value = {"numbers": numbers, "merchant_identity": merchant_identity, "consumption_time": datetime(1970, 1, 1),
                 "sums": 0, "exchanged": 1, "credit": credit, "manager_numbers": manager, "gift": 1,
                 "exchange_time": datetime.now(), "credit_rest": credit}

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40507, "get collection credit failed"
        credit_identity = collection.insert_one(value).inserted_id
        credit_identity = str(credit_identity)
        g_log.debug("insert consumption %s", value)

        return 40500, credit_identity
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40508, "exception"


def consumer_credit_retrieve(numbers, merchant_identity):
    """
    获取用户的积分
    :param numbers: 用户号码
    :return: (40600, (consumer, credit)/成功，(>40600, "errmsg")/失败
    """
    try:
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid merchant manager %s", numbers)
            return 40601, "invalid merchant manager"

        if merchant_identity:
            # 平台读取所有操作纪录
            return consumer_credit_retrieve_one(numbers, merchant_identity)

        code, consumer = consumer_retrieve_with_numbers(numbers)
        if code != 20200:
            g_log.error("retrieve consumer %s failed", numbers)
            return 40602, "retrieve consumer failed"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40603, "get collection credit failed"
        credit = collection.find({"numbers": numbers, "type": {"$ne": "r"},
                                  "expire_time": {"$gte": datetime.now()}}).sort("merchant_identity")
        g_log.debug("consumer has %s credit", credit.count())

        return 40600, (consumer, credit)
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40604, "exception"


def consumer_credit_retrieve_one(numbers, merchant_identity):
    try:
        code, consumer = consumer_retrieve_with_numbers(numbers)
        if code != 20200:
            g_log.error("retrieve consumer %s failed", numbers)
            return 40610, "retrieve consumer failed"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40611, "get collection credit failed"
        credit = collection.find({"numbers": numbers, "merchant_identity": merchant_identity, "type": {"$ne": "r"},
                                  "expire_time": {"$gte": datetime.now()}})
        g_log.debug("consumer has %s credit", credit.count())

        return 40600, (consumer, credit)
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40612, "exception"


def consume_credit(**kwargs):
    """
    用户消费
    :param numbers: 用户号码
    :return: (40700, (consumer, credit)/成功，(>40700, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40701, "invalid phone number"

        credit_identity = kwargs.get("credit_identity")
        if not credit_identity:
            g_log.error("lost credit identity")
            return 40702, "illegal argument"

        # merchant_identity = kwargs.get("merchant_identity")
        # if not merchant_identity:
        #     g_log.error("lost merchant identity")
        #     return 40703, "illegal argument"

        credit = kwargs.get("credit")
        if not credit or credit < 0:
            g_log.error("credit %s illegal", credit)
            return 40704, "illegal argument"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40705, "get collection credit failed"

        # # 更新积分总量
        # result = collection.find_one({"numbers": numbers, "_id": ObjectId(credit_identity),
        #                                           "exchanged": 1, "credit_rest": {"$gte": credit}})
        result = collection.find_one_and_update({"numbers": numbers, "_id": ObjectId(credit_identity), "exchanged": 1,
                                                 "credit_rest": {"$gte": credit}},
                                                {"$inc": {"credit_rest": -credit}},
                                                return_document=ReturnDocument.AFTER)
        if not result:
            # g_log.warning("match count:%s, modified count:%s", result.matched_count, result.modified_count)
            g_log.warning("consume credit failed")
            return 40706, "consume credit failed"
        merchant_identity = result["merchant_identity"]

        # 保存积分消费记录
        collection = get_mongo_collection("credit_record")
        if not collection:
            g_log.error("get collection credit record failed")
            return 40707, "get collection credit record failed"
        value = {"numbers": numbers, "credit_identity": credit_identity, "merchant_identity": merchant_identity,
                 "consume_time": datetime.now(), "credit": credit}
        credit_record_identity = collection.insert_one(value).inserted_id
        credit_record_identity = str(credit_record_identity)
        g_log.debug("insert credit record %s", credit_record_identity)

        return 40700, credit_record_identity
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40708, "exception"


def consume_credit_retrieve(**kwargs):
    """
    积分消费查询
    :param numbers: 用户号码
    :return: (40800, (consumer, credit)/成功，(>40800, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40801, "invalid phone number"

        begin_time = kwargs.get("begin_time", datetime(1970, 1, 1))
        end_time = kwargs.get("end_time", datetime.now())
        limit = kwargs.get("limit", 0)

        collection = get_mongo_collection("credit_record")
        if not collection:
            g_log.error("get collection credit record failed")
            return 40802, "get collection credit record failed"

        records = collection.find({"numbers": numbers, "consume_time": {"$gte": begin_time},
                                   "consume_time": {"$lte": end_time}}, limit=limit).sort("merchant_identity")
        g_log.debug("consumer has %s credit record", records.count())

        return 40800, records
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40803, "exception"


def interchange_credit_create(**kwargs):
    """
    兑换后新积分
    gift 消费记录/0，赠送积分/1
    :param kwargs: {"numbers": "18688982240", "merchant_identity": "", "credit": 350}
    :return: (40520, credit_identity)/成功，(>40520, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40931, "invalid phone number"

        merchant_identity = kwargs.get("merchant_identity")
        if not merchant_identity:
            g_log.error("lost merchant")
            return 40932, "illegal argument"

        credit = kwargs.get("credit")
        if not credit or credit < 0:
            g_log.error("credit %s illegal", credit)
            return 40933, "illegal argument"

        # 过期时间不变
        expire_time = kwargs.get("expire_time")
        if not expire_time:
            g_log.warning("lost expire time")
            expire_time = datetime(1970, 1, 1)
        # else:
        #     expire_time = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S").date()
        g_log.debug("expire_time %s", expire_time)

        # 检查商家是否存在，TODO... user_is_merchant_manager包含该检查
        if not merchant_exist(merchant_identity):
            g_log.error("merchant %s not exit", merchant_identity)
            return 40934, "illegal argument"

        # 用户ID，商户ID，消费金额，消费时间，是否兑换成积分，兑换成多少积分，兑换操作管理员，兑换时间，积分剩余量
        value = {"numbers": numbers, "merchant_identity": merchant_identity, "consumption_time": datetime(1970, 1, 1),
                 "sums": 0, "exchanged": 1, "credit": credit, "manager_numbers": "", "type": "i",
                 "exchange_time": datetime.now(), "expire_time": expire_time, "credit_rest": credit}

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40937, "get collection credit failed"
        credit_identity = collection.insert_one(value).inserted_id
        credit_identity = str(credit_identity)
        g_log.debug("insert interchange %s", value)

        return 40930, credit_identity
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40938, "exception"


def credit_interchange(**kwargs):
    """
    用户兑换积分
    :param numbers: 用户号码
    :return: (40900, (consumer, credit)/成功，(>40900, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 40911, "invalid account"

        credit_identity = kwargs.get("credit_identity")
        if not credit_identity:
            g_log.error("lost credit identity")
            return 40912, "illegal argument"

        to_merchant = kwargs.get("to_merchant")
        if not to_merchant:
            g_log.error("lost to merchant")
            return 40913, "illegal argument"

        from_merchant = kwargs.get("from_merchant")
        if not from_merchant:
            g_log.error("lost from merchant")
            return 40913, "illegal argument"

        credit = kwargs.get("credit")
        if not credit or credit < 0:
            g_log.error("credit %s illegal", credit)
            return 40914, "illegal argument"
        from_credit = credit

        exec_interchange = kwargs.get("exec_interchange", 0)

        code, message = credit_conversion(from_merchant, to_merchant, from_credit)
        if code != 51100:
            g_log.error("credit conversion failed, %s", message)
            return 40922, "credit conversion failed"

        to_credit = int(message)
        fee = to_credit * 5 / 100   # 5%手续费
        to_credit -= fee

        # 只计算to_credit
        if not exec_interchange:
            return 40900, (to_credit, fee)

        # 检查to_merchant是否允许兑换，检查已发行小于发行积分上限
        code, message = credit_exceed_upper(**{"merchant_identity": to_merchant, "credit": to_credit,
                                               "allow_last": "yes"})
        if code != 61000 or not bool(message):
            g_log.error("to merchant issued exceed upper bound")
            return 40923, "issued exceed upper bound"

        # 检查from_merchant是否有足够余额，检查余额为正
        code, message = balance_overdraft(from_merchant)
        if code != 61100:
            g_log.error("balance overdraft, %s", message)
            return 40924, "balance overdraft"

        collection = get_mongo_collection("credit")
        if not collection:
            g_log.error("get collection credit failed")
            return 40915, "get collection credit failed"

        # 更新换出积分量
        result = collection.find_one_and_update({"numbers": numbers, "_id": ObjectId(credit_identity), "exchanged": 1,
                                                 "credit_rest": {"$gte": credit}},
                                                {"$inc": {"credit_rest": -credit}},
                                                return_document=ReturnDocument.AFTER)
        if not result:
            g_log.warning("interchange credit failed")
            return 40916, "interchange credit failed"
        from_merchant = result["merchant_identity"]

        # 创建兑换成的新积分
        code, credit_new = interchange_credit_create(**{"numbers": numbers, "merchant_identity": to_merchant,
                                                        "credit": to_credit, "expire_time": result["expire_time"]})
        if code != 40930:
            g_log.error("create interchange credit failed")
            return 40917, "create interchange credit failed"

        # 更新兑换入的商家flow参数(积分互换)
        code, message = merchant_credit_update_batch(**{"numbers": "10000", "merchant_identity": to_merchant,
                                                        "items": [("interchange_in", to_credit), ("issued", to_credit),
                                                                  ("balance", to_credit)]})
        if code != 60400:
            g_log.error("update from merchant flow failed, %s", message)
            return 40920, "update from merchant flow failed"

        # 更新兑换出的商家flow参数(积分互换)
        code, message = merchant_credit_update_batch(**{"numbers": "10000", "merchant_identity": from_merchant,
                                                        "items": [("interchange_out", from_credit),
                                                                  ("issued", -from_credit), ("balance", -credit)]})
        if code != 60400:
            g_log.error("update to merchant flow failed, %s", message)
            return 40921, "update to merchant flow failed"

        # 保存积分兑换记录
        collection = get_mongo_collection("interchange_record")
        if not collection:
            g_log.error("get collection credit record failed")
            return 40918, "get collection credit record failed"
        value = {"numbers": numbers, "credit_identity": credit_identity, "from_merchant": from_merchant,
                 "to_merchant": to_merchant, "interchange_time": datetime.now(), "from_credit": from_credit,
                 "to_credit": to_credit, "fee": fee}
        interchange_record_identity = collection.insert_one(value).inserted_id
        interchange_record_identity = str(interchange_record_identity)
        g_log.debug("insert credit record %s", interchange_record_identity)

        # fee保存入平台账号
        collection = get_mongo_collection("fee")
        if not collection:
            g_log.error("get collection fee failed")
            return 40922, "get collection fee failed"
        value = {"interchange_record": interchange_record_identity, "interchange_time": datetime.now(),
                 "merchant": from_merchant, "fee": fee}
        fee_identity = collection.insert_one(value).inserted_id
        fee_identity = str(fee_identity)
        g_log.debug("insert fee %s", fee_identity)

        # TODO... 考虑返回(兑换后的原积分， 兑换后的新积分)
        return 40900, (to_credit, fee)
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 40919, "exception"


def credit_interchange_retrieve(**kwargs):
    """
    积分兑换查询
    :param numbers: 用户号码
    :return: (40800, (consumer, credit)/成功，(>40800, "errmsg")/失败
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_consumer(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 41011, "invalid phone number"

        begin_time = kwargs.get("begin_time", datetime(1970, 1, 1))
        end_time = kwargs.get("end_time", datetime.now())
        limit = kwargs.get("limit", 0)

        collection = get_mongo_collection("interchange_record")
        if not collection:
            g_log.error("get collection interchange record failed")
            return 41012, "get collection interchange record failed"

        records = collection.find({"numbers": numbers, "interchange_time": {"$gte": begin_time},
                                   "interchange_time": {"$lte": end_time}},
                                  limit=limit).sort(["from_merchant", "to_merchant"])
        g_log.debug("consumer has %s interchange record", records.count())

        return 41000, records
    except Exception as e:
        g_log.error("%s %s", e.__class__, e)
        return 41013, "exception"


def credit_copy_from_document_base(material, value):
    """
    mongo中的单条积分记录赋值给CreditMaterial
    :param material: CreditMaterial
    :param value: 单个积分document
    :return:
    """
    g_log.debug(value)
    material.type = value["type"]
    material.sums = value["sums"]

    material.consumption_time = value["consumption_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.exchanged = value["exchanged"]
    material.credit = value["credit"]
    # material.manager_numbers = value["manager_numbers"]
    # material.exchange_time = value["exchange_time"].strftime("%Y-%m-%d %H:%M:%S")
    material.expire_time = value["expire_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.credit_rest = value["credit_rest"]

    material.identity = str(value["_id"])
    # material.numbers = value["numbers"]


def credit_copy_from_document(material, value):
    """
    mongo中的单条积分记录赋值给CreditMaterial
    :param material: CreditMaterial
    :param value: 单个积分document
    :return:
    """
    g_log.debug(value)
    material.type = value["type"]
    material.sums = value["sums"]

    material.consumption_time = value["consumption_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.exchanged = value["exchanged"]
    material.credit = value["credit"]
    material.manager_numbers = value["manager_numbers"]
    material.exchange_time = value["exchange_time"].strftime("%Y-%m-%d %H:%M:%S")
    material.expire_time = value["expire_time"].strftime("%Y-%m-%d %H:%M:%S")

    material.credit_rest = value["credit_rest"]

    material.identity = str(value["_id"])
    # material.numbers = value["numbers"]


def consume_copy_from_document(material, value):
    """
    mongo中的单条积分记录赋值给ConsumeMaterial
    :param material: ConsumeMaterial
    :param value: 单个积分document
    :return:
    """
    material.consume_time = value["consume_time"].strftime("%Y-%m-%d %H:%M:%S")
    material.credit_identity = value["credit_identity"]
    material.credit = value["credit"]

    material.identity = str(value["_id"])


def interchange_copy_from_document(material, value):
    """
    mongo中的单条积分记录赋值给ExchangeMaterial
    :param material: ExchangeMaterial
    :param value: 单个积分document
    :return:
    """
    material.interchange_time = value["interchange_time"].strftime("%Y-%m-%d %H:%M:%S")
    # material.credit_identity = value["credit_identity"]
    material.from_credit = value["credit"]
    material.to_credit = value["credit"]

    material.identity = str(value["_id"])
