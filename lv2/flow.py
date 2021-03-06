# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from datetime import datetime
import time
import hashlib
import httplib
from pymongo.collection import ReturnDocument
from mongo_connection import get_mongo_collection
import common_pb2
import package
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from account_valid import account_is_valid_merchant, account_is_platform, account_is_valid_consumer
from account_auxiliary import verify_session_key, identity_to_numbers
from merchant import user_is_merchant_manager, merchant_is_verified, merchant_retrieve_with_merchant_identity_only, \
    merchant_material_copy_from_document, merchant_update_alipay
from flow_auxiliary import credit_exceed_upper


class Flow():
    """
    商家积分变动模块，命令号<600
    request：请求包解析后的pb格式
    """
    def __init__(self, request):
        self.request = request
        self.head = request.head
        self.cmd = self.head.cmd
        self.seq = self.head.seq
        self.numbers = self.head.numbers
        self.session_key = self.head.session_key

        self.code = 1   # 模块号(2位) + 功能号(2位) + 错误号(2位)
        self.message = ""

    def enter(self):
        """
        处理具体业务
        :return: 0/不回包给前端，pb/正确返回，timeout/超时
        """
        try:
            if 508 != self.cmd:     # alipay异步通知
                # 验证登录态，某些命令可能不需要登录态，此处做判断
                code, message = verify_session_key(self.numbers, self.session_key)
                if 10400 != code:
                    g_log.debug("verify session key failed, %s, %s", code, message)
                    return package.error_response(self.cmd, self.seq, 60001, "invalid session key")

            command_handle = {501: self.merchant_credit_flow_retrieve, 502: self.merchant_allow_exchange_in,
                              503: self.merchant_recharge, 504: self.merchant_withdrawals,
                              505: self.balance_record_retrieve, 506: self.balance_retrieve,
                              507: self.recharge_trade_no_retrieve, 508: self.alipay_async_notify}

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
            from print_exception import print_exception
            print_exception()
            g_log.error("%s", e)
            return 0

    def merchant_credit_flow_retrieve(self):
        """
        读取商家积分、余额详情
        :return:
        """
        try:
            body = self.request.merchant_credit_flow_retrieve_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            identity = body.identity

            if not numbers:
                # 根据包体中的merchant_identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60101
                    self.message = "missing argument"
                    return 1

            if merchant_identity:
                g_log.debug("%s retrieve merchant %s credit", numbers, merchant_identity)
            else:
                g_log.debug("%s retrieve all merchant credit", numbers)
            self.code, self.message = merchant_credit_flow_retrieve(numbers, merchant_identity)

            if 60100 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve merchant credit done"

                credit_flow = response.merchant_credit_flow_retrieve_response.credit_flow
                last_merchant = ""
                # 遍历管理员所有商家
                for value in self.message:
                    if last_merchant != value["merchant_identity"]:
                        credit_flow_one = credit_flow.add()
                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value["merchant_identity"])
                        merchant_material_copy_from_document(credit_flow_one.merchant, merchants[0])
                        material = credit_flow_one.material
                    # aggressive_record_one = aggressive_record.add()
                    last_merchant = value["merchant_identity"]
                    merchant_flow_copy_from_document(material, value)

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def merchant_allow_exchange_in(self):
        """
        商家允许积分转入
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.merchant_allow_exchange_in_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            identity = body.identity

            if not numbers:
                # 根据包体中的merchant_identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60201
                    self.message = "missing argument"
                    return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity}
            # g_log.debug("merchant exchange in: %s", kwargs)
            self.code, self.message = merchant_allow_exchange_in(**kwargs)

            if 60200 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "merchant allow exchange in done"

                response.merchant_allow_exchange_in_response.allow = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def merchant_recharge(self):
        """
        商家充值
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.merchant_recharge_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            money = body.money
            identity = body.identity
            trade_no = body.trade_no

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60301
                    self.message = "missing argument"
                    return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "money": money, "trade_no": trade_no}
            g_log.debug("merchant recharge: %s", kwargs)
            self.code, self.message = merchant_recharge(**kwargs)

            if 60300 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "merchant recharge done"
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def merchant_withdrawals(self):
        """
        商家提现
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.merchant_withdrawals_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            money = body.money
            identity = body.identity

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60401
                    self.message = "missing argument"
                    return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "money": money}
            g_log.debug("merchant withdrawals: %s", kwargs)
            self.code, self.message = merchant_withdrawals(**kwargs)

            if 60400 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "merchant withdrawals done"
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def balance_record_retrieve(self):
        """
        读取充值、提现纪录
        :return:
        """
        try:
            body = self.request.merchant_balance_record_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            identity = body.identity

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60501
                    self.message = "missing argument"
                    return 1

            if merchant_identity:
                g_log.debug("%s retrieve merchant %s recharge record", numbers, merchant_identity)
            else:
                g_log.debug("%s retrieve all merchant recharge record", numbers)
            self.code, self.message = balance_record_retrieve(numbers, merchant_identity)

            if 60500 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve recharge record done"

                balance_record = response.merchant_balance_record_response.balance_record
                last_merchant = ""
                # 遍历管理员所有商家
                for value in self.message:
                    if last_merchant != value["merchant_identity"]:
                        balance_record_one = balance_record.add()
                        # 商家资料
                        code, merchants = merchant_retrieve_with_merchant_identity_only(value["merchant_identity"])
                        merchant_material_copy_from_document(balance_record_one.merchant, merchants[0])
                        aggressive_record = balance_record_one.aggressive_record
                    aggressive_record_one = aggressive_record.add()
                    last_merchant = value["merchant_identity"]
                    balance_record_copy_from_document(aggressive_record_one, value)

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def balance_retrieve(self):
        """
        读取帐户余额
        :return:
        """
        try:
            body = self.request.merchant_balance_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            identity = body.identity

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60601
                    self.message = "missing argument"
                    return 1

            g_log.debug("%s retrieve merchant %s balance", numbers, merchant_identity)
            self.code, self.message = balance_retrieve(numbers, merchant_identity)

            if 60600 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve balance done"

                response.merchant_balance_response.balance = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def recharge_trade_no_retrieve(self):
        """
        商家充值
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.merchant_recharge_trade_no_request
            numbers = body.numbers
            merchant_identity = body.merchant_identity
            money = body.money
            identity = body.identity

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 60701
                    self.message = "missing argument"
                    return 1

            kwargs = {"numbers": numbers, "merchant_identity": merchant_identity, "money": money}
            g_log.debug("merchant recharge trade no: %s", kwargs)
            self.code, self.message = recharge_trade_no(**kwargs)

            if 60700 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "query recharge trade no done"

                body = response.merchant_recharge_trade_no_response
                body.trade_no = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def alipay_async_notify(self):
        """
        商家充值alipay异步通知
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.alipay_async_notify_request
            # trade_status = body.trade_status
            # sign_type = body.sign_type
            # sign = body.sign
            # notify_type = body.notify_type
            # notify_id = body.notify_id
            # buyer_id = body.buyer_id
            # buyer_email = body.buyer_email
            # out_trade_no = body.out_trade_no
            trade_no = body.trade_no
            # seller_email = body.seller_email
            # seller_id = body.seller_id
            # total_fee = float(body.total_fee)
            # notify_time = body.notify_time
            # gmt_create = body.gmt_create
            # gmt_payment = body.gmt_payment

            g_log.debug("deal alipay async notify: %s", trade_no)
            self.code, self.message = alipay_async_notify(self.request.alipay_async_notify_request)

            if 60800 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "alipay async notify done"

                body = response.alipay_async_notify_response
                body.message = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def dummy_command(self):
        # 无效的命令，不回包
        g_log.debug("unknow command %s", self.cmd)
        return 0


def enter(request):
    """
    模块入口
    :param request: 解析后的pb格式
    :return: 0/不回包给前端，pb/正确返回，timeout/超时
    """
    try:
        flow = Flow(request)
        return flow.enter()
    except Exception as e:
        g_log.error("%s", e)
        return 0


def bond_to_upper_bound(bond, ratio):
    """
    根据保证金计算商家积分上限 ＝ 基础分（10000）＋ 保证金 X 积分汇率
    :param bond:
    :return:
    """
    # TODO... 保证金检查
    return bond * ratio + 10000


def upper_bound_update(**kwargs):
    """
    商家积分上限变更，保证金变更的时候调
    :param kwargs: {"numbers": 1000000, "merchant_identity": "", "bond": 1000}
    :return: (60100, "yes")/成功，(>60100, "errmsg")/失败
    """
    try:
        # 检查请求用户numbers必须是平台管理员
        numbers = kwargs.get("numbers", "")
        if not account_is_platform(numbers):
            g_log.warning("not platform %s", numbers)
            return 60311, "no privilege"

        # 必须是已认证商家，在更新保证金已经做过验证，此处省略
        merchant_identity = kwargs.get("merchant_identity", "")

        bond = kwargs.get("bond", 0)
        ratio = kwargs.get("ratio", 0)
        upper_bound = bond_to_upper_bound(bond, ratio)
        value = {"merchant_identity": merchant_identity, "upper_bound": upper_bound, "deleted": 0}

        # 存入数据库
        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60313, "get collection flow failed"
        flow = collection.find_one_and_update({"merchant_identity": merchant_identity, "deleted": 0}, {"$set": value})

        # 第一次更新，则插入一条
        if not flow:
            g_log.debug("insert new flow")
            flow = collection.insert_one(value)
        if not flow:
            g_log.error("update merchant %s credit upper bound failed", merchant_identity)
            return 60314, "update failed"
        g_log.debug("update upper bound succeed")

        # 更新记录入库
        collection = get_mongo_collection("flow_record")
        if not collection:
            g_log.error("get collection flow record failed")
            return 60315, "get collection flow record failed"
        quantization = "bond:%d, bound:%d" % (bond, upper_bound)
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": datetime.now(),
                                        "operator": numbers, "quantization": quantization})
        if not result:
            g_log.error("insert flow record failed")
            # return 60316, "insert flow record failed"

        return 60300, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60317, "exception"


def merchant_credit_update(**kwargs):
    """
    商家积分变更
    积分类型：可发行积分总量、已发行积分、积分互换IN & OUT、用户消费积分、账户余额变更
    mode=["may_issued", "issued", "interchange_in", "interchange_out", "consumption", "balance"]
    :param kwargs: {"numbers": 11868898224, "merchant_identity": "", "mode": may_issued, "supplement": 1000}
    :return:
    """
    try:
        # 检查请求用户numbers必须是平台管理员或者商家管理员
        numbers = kwargs.get("numbers", "")
        if not account_is_platform(numbers) and not account_is_valid_merchant(numbers):
            g_log.warning("not manager and not platform, %s", numbers)
            return 60411, "no privilege"

        # 必须是已认证商家，在补充可发行积分总量时已经做过验证，此处省略
        merchant_identity = kwargs.get("merchant_identity", "")
        if not account_is_platform(numbers):
            merchant = user_is_merchant_manager(numbers, merchant_identity)
            if not merchant:
                g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
                return 60412, "not manager"
            merchant_founder = merchant["merchant_founder"]
            g_log.debug("merchant %s founder %s", merchant_identity, merchant_founder)

        mode = kwargs.get("mode", "")
        modes = ["may_issued", "issued", "interchange_in", "interchange_out", "consumption", "balance"]
        if mode not in modes:
            g_log.error("not supported mode %s", mode)
            return 60413, "not supported mode"
        # TODO... 积分检查
        supplement = kwargs.get("supplement", 0)
        value = {"merchant_identity": merchant_identity, mode: supplement, "deleted": 0}

        # 存入数据库
        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60414, "get collection flow failed"
        flow = collection.find_one_and_update({"merchant_identity": merchant_identity, "deleted": 0},
                                              {"$inc": {mode: supplement}}, return_document=ReturnDocument.BEFORE)

        # 第一次更新，则插入一条
        if not flow:
            g_log.debug("insert new flow")
            flow = collection.insert_one(value)
            if not flow:
                g_log.error("update merchant %s %s credit failed", merchant_identity, mode)
                return 60415, "update failed"
        g_log.debug("update merchant %s credit succeed", mode)
        # last = flow[mode]    # 更新前的值

        # 更新记录入库
        collection = get_mongo_collection("flow_record")
        if not collection:
            g_log.error("get collection flow record failed")
            return 60416, "get collection flow record failed"
        quantization = "mode:%s, supplement:%d" % (mode, supplement)
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": datetime.now(),
                                        "operator": numbers, "quantization": quantization})
        if not result:
            g_log.error("insert flow record failed")

        # return 60400, last
        return 60400, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60417, "exception"


def merchant_credit_update_batch(**kwargs):
    """
    商家积分变更
    积分类型：可发行积分总量、已发行积分、积分互换IN & OUT、用户消费积分、账户余额变更
    mode=["may_issued", "issued", "interchange_in", "interchange_out", "consumption", "balance"]
    :param kwargs: {"numbers": 11868898224, "merchant_identity": "", "items": [("may_issued", 1000), ...]}
    :return:
    """
    try:
        # 检查请求用户numbers必须是平台管理员
        numbers = kwargs.get("numbers", "")
        merchant_identity = kwargs.get("merchant_identity", "")
        if numbers != "10000":
            if not account_is_valid_merchant(numbers):
                g_log.warning("not manager %s", numbers)
                return 60421, "no privilege"
            # 必须是已认证商家，在补充可发行积分总量时已经做过验证，此处省略

            merchant = user_is_merchant_manager(numbers, merchant_identity)
            if not merchant:
                g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
                return 60422, "not manager"
            merchant_founder = merchant["merchant_founder"]
            g_log.debug("merchant %s founder %s", merchant_identity, merchant_founder)

        modes = ["may_issued", "issued", "interchange_in", "interchange_out", "consumption", "balance"]
        items = kwargs.get("items", "")
        inc = {}
        value = {"merchant_identity": merchant_identity, "deleted": 0}
        for item in items:
            mode = item[0]
            supplement = item[1]
            if mode not in modes:
                g_log.error("not supported mode %s", mode)
                return 60423, "not supported mode"
            # TODO... 积分检查
            # supplement = kwargs.get("supplement", 0)
            inc[mode] = supplement
            value[mode] = supplement

        # 存入数据库
        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60424, "get collection flow failed"
        flow = collection.find_one_and_update({"merchant_identity": merchant_identity, "deleted": 0}, {"$inc": inc})

        # 第一次更新，则插入一条
        if not flow:
            g_log.debug("insert new flow")
            flow = collection.insert_one(value)
        if not flow:
            g_log.error("update merchant %s credit failed", merchant_identity)
            return 60425, "update failed"
        g_log.debug("update merchant %s credit succeed", merchant_identity)

        # 更新记录入库
        collection = get_mongo_collection("flow_record")
        if not collection:
            g_log.error("get collection flow record failed")
            return 60426, "get collection flow record failed"
        quantization = "&".join(["mode:" + mode + ", supplement:" + str(supplement) for (mode, supplement) in items])
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": datetime.now(),
                                        "operator": numbers, "quantization": quantization})
        if not result:
            g_log.error("insert flow record failed")

        return 60400, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60427, "exception"


def merchant_credit_flow_retrieve(numbers, merchant_identity):
    """
    读取商家积分详情，没给出merchant_identity则读取全部
    :param numbers: 平台账号或管理员账号
    :param merchant_identity: 商家ID
    :return:
    """
    try:
        if not merchant_identity:
            # 平台读取所有操作纪录
            return merchant_credit_flow_retrieve_all(numbers)

        # 检查管理员和商家关系
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60112, "not manager"

        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60113, "get collection flow failed"
        records = collection.find({"merchant_identity": merchant_identity, "deleted": 0})
        if not records:
            g_log.error("retrieve flow failed")
            return 60114, "retrieve failed"

        return 60100, records
    except Exception as e:
        g_log.error("%s", e)
        return 60115, "exception"


def merchant_credit_flow_retrieve_all(numbers):
    """
    查找所有商家的操作纪录
    :param numbers:
    :return:
    """
    try:
        if not account_is_platform(numbers):
            g_log.error("%s not platform", numbers)
            return 60116, "no privilege"

        # 广播查找所有商家的积分详情
        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60117, "get collection flow failed"
        records = collection.find({"deleted": 0}).sort("merchant_identity")
        if not records:
            g_log.error("retrieve flow failed")

        return 60100, records
    except Exception as e:
        g_log.error("%s", e)
        return 60118, "exception"


def merchant_allow_exchange_in(**kwargs):
    """
    商家是否允许积分转入
    :param numbers: 平台账号或管理员账号
    :param merchant_identity: 商家ID
    :return:
    """
    try:
        # 检查要创建者numbers
        numbers = kwargs.get("numbers", "")
        merchant_identity = kwargs.get("merchant_identity")

        # 检查管理员和商家关系
        if not account_is_valid_consumer(numbers):
            g_log.error("invalid account, %s", numbers)
            return 60211, "invalid account"

        if merchant_is_verified(merchant_identity) != "y":
            g_log.debug("merchant %s not verified", merchant_identity)
            return 60213, "not verified"

        code, message = credit_exceed_upper(**{"merchant_identity": merchant_identity, "allow_last": "yes"})

        return 60200, "yes" if bool(message) else "no"
    except Exception as e:
        g_log.error("%s", e)
        return 60212, "exception"


# pragma 商家充值API
def merchant_recharge(**kwargs):
    """
    商家充值，未认证商家不允许操作
    :param kwargs: {"numbers": 118688982240, "merchant_identity": "", "money": 100}
    :return: (60300, "yes")/成功，(>60300, "errmsg")/失败
    """
    try:
        # 检查要请求用户numbers必须是平台管理员
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_merchant(numbers):
            g_log.warning("not manager %s", numbers)
            return 60311, "not manager"

        # 检查管理员和商家关系
        merchant_identity = kwargs.get("merchant_identity", "")
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60312, "not manager"
        # merchant_founder = merchant["merchant_founder"]
        # g_log.debug("merchant %s founder %s", merchant_identity, merchant_founder)

        # 认证用户才可以充值
        if not merchant_is_verified(merchant_identity):
            g_log.error("merchant %s not verified", merchant_identity)
            return 60313, "not verified"

        # 充值金额换成积分值 （充值金额 * 金额积分比例系数）
        money = kwargs.get("money", 0)
        collection = get_mongo_collection("parameters")
        if not collection:
            g_log.error("get collection parameters failed")
            return 60318, "get collection parameters failed"

        business_parameters = collection.find_one({"merchant_identity": merchant_identity})
        if not business_parameters:
            g_log.error("get merchant %s parameters failed", merchant_identity)
            return 60319, "get merchant parameters failed"
        balance = money * business_parameters["balance_ratio"]

        # 存入数据库
        code, message = merchant_credit_update(**{"numbers": numbers, "merchant_identity": merchant_identity,
                                                  "mode": "balance", "supplement": balance})
        if code != 60400:
            g_log.error("merchant recharge failed, %s", message)
            return 60314, "recharge failed"
        # last = int(message)
        # g_log.debug("last balance: %d", last)

        trade_no = kwargs.get("trade_no", "")
        # 更新记录入库
        collection = get_mongo_collection("balance_record")
        if not collection:
            g_log.error("get collection balance record failed")
            return 60315, "get collection balance record failed"
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": datetime.now(),
                                        "operator": numbers, "money": money, "type": "recharge", "trade_no": trade_no})
        if not result:
            g_log.error("insert recharge record failed")
            return 60316, "insert recharge record failed"

        # collection = get_mongo_collection("trade_no")
        # if not collection:
        #     g_log.error("get collection trade_no failed")
        #     return 60320, "get collection trade_no failed"
        # result = collection.find_one_and_update({"merchant_identity": merchant_identity, "trade_no": trade_no},
        #                                         {"$set": {"state": "done"}})
        # if not result:
        #     g_log.warning("can not find trade no: %s", trade_no)

        return 60300, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60317, "exception"


def query_withdrawals_times(merchant):
    """
    获取商家今天提现次数
    :param merchant:
    :return:
    """
    collection = get_mongo_collection("withdrawals")
    if not collection:
        g_log.error("get collection withdrawals failed")
        return 999999

    withdrawals = collection.find_one({"merchant_identity": merchant, "date": datetime.now().strftime('%Y-%m-%d')})
    if not withdrawals:
        return 0
    return withdrawals["times"]


def update_withdrawals_times(merchant, times):
    """
    获取商家今天提现次数
    :param merchant:
    :return:
    """
    collection = get_mongo_collection("withdrawals")
    if not collection:
        g_log.error("get collection withdrawals failed")
        return "no"

    # flow = collection.find_one_and_update({"merchant_identity": merchant_identity, "deleted": 0},
    #                                           {"$inc": {mode: supplement}}, return_document=ReturnDocument.BEFORE)

    withdrawals = collection.find_one_and_update({"date": datetime.now().strftime('%Y-%m-%d'),
                                                 "merchant_identity": merchant}, {"$inc": {"times": times}})
    if not withdrawals:
        g_log.debug("first withdrawals")
        withdrawals = collection.insert_one({"merchant_identity": merchant, "date": datetime.now().strftime('%Y-%m-%d'),
                                             "times": 1})
        if not withdrawals:
            return "no"

    return "yes"


def merchant_withdrawals(**kwargs):
    """
    商家提现，未认证商家不允许操作
    :param kwargs: {"numbers": 118688982240, "merchant_identity": "", "money": 100}
    :return: (60400, "yes")/成功，(>60400, "errmsg")/失败
    """
    try:
        # 检查要请求用户numbers必须是平台管理员
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_merchant(numbers):
            g_log.warning("not manager %s", numbers)
            return 60411, "not manager"

        # 检查管理员和商家关系
        merchant_identity = kwargs.get("merchant_identity", "")
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60412, "not manager"
        # merchant_founder = merchant["merchant_founder"]
        # g_log.debug("merchant %s founder %s", merchant_identity, merchant_founder)

        # 认证用户才可以充值
        if not merchant_is_verified(merchant_identity):
            g_log.error("merchant %s not verified", merchant_identity)
            return 60413, "not verified"

        # 检查今天是否已经提现
        if query_withdrawals_times(merchant_identity) > 0:
            g_log.error("had withdrawals today")
            return 60418, "exceed"

        # 提现金额换成积分值 （提现金额 * 金额积分比例系数）
        money = kwargs.get("money", 0)
        collection = get_mongo_collection("parameters")
        if not collection:
            g_log.error("get collection parameters failed")
            return 60418, "get collection parameters failed"

        business_parameters = collection.find_one({"merchant_identity": merchant_identity})
        if not business_parameters:
            g_log.error("get merchant %s parameters failed", merchant_identity)
            return 60419, "get merchant parameters failed"
        balance = money * business_parameters["balance_ratio"]

        # 存入数据库
        code, message = merchant_credit_update(**{"numbers": numbers, "merchant_identity": merchant_identity,
                                                  "mode": "balance", "supplement": -balance})
        if code != 60400:
            g_log.error("merchant withdrawals failed, %s", message)
            return 60414, "withdrawals failed"
        # last = int(message)
        # g_log.debug("last balance: %d", last)

        if update_withdrawals_times(merchant_identity, 1) == "no":
            g_log.warning("update withdrawals %d times failed", 1)

        # 更新记录入库
        collection = get_mongo_collection("balance_record")
        if not collection:
            g_log.error("get collection balance record failed")
            return 60400, "get collection balance record failed"
            # return 60415, "get collection balance record failed"
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": datetime.now(),
                                        "operator": numbers, "money": money, "type": "withdrawals", "state": "pending"})
        if not result:
            g_log.error("insert withdrawals record failed")
            return 60400, "insert withdrawals record failed"
            # return 60416, "insert withdrawals record failed"
        return 60400, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60417, "exception"


def balance_record_retrieve(numbers, merchant_identity):
    """
    读取充值、提现纪录，没给出merchant_identity则读取全部
    :param numbers: 平台账号或管理员账号
    :param merchant_identity: 商家ID
    :return:
    """
    try:
        if not merchant_identity:
            # 平台读取所有操作纪录
            return balance_record_retrieve_all(numbers)

        # 检查管理员和商家关系
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60512, "not manager"

        # 广播查找所有商家的经营参数更新纪录
        collection = get_mongo_collection("balance_record")
        if not collection:
            g_log.error("get collection balance record failed")
            return 60513, "get collection balance record failed"
        records = collection.find({"merchant_identity": merchant_identity})
        if not records:
            g_log.error("retrieve balance record failed")
            return 60514, "retrieve balance record failed"

        return 60500, records
    except Exception as e:
        g_log.error("%s", e)
        return 60514, "exception"


def balance_record_retrieve_all(numbers):
    """
    查找所有商家的充值操作纪录
    :param numbers:
    :return:
    """
    try:
        if not account_is_platform(numbers):
            g_log.error("%s not platform", numbers)
            return 60515, "no privilege"

        # 广播查找所有商家的经营参数更新纪录
        collection = get_mongo_collection("balance_record")
        if not collection:
            g_log.error("get collection balance record failed")
            return 60516, "get collection balance record failed"
        records = collection.find({}).sort("merchant_identity")
        if not records:
            g_log.error("retrieve balance record failed")

        return 60500, records
    except Exception as e:
        g_log.error("%s", e)
        return 60517, "exception"


def balance_retrieve(numbers, merchant_identity):
    """
    读取商家帐户余额
    :param numbers: 平台账号或管理员账号
    :param merchant_identity: 商家ID
    :return:
    """
    try:
        # 检查管理员和商家关系
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60611, "not manager"

        collection = get_mongo_collection("flow")
        if not collection:
            g_log.error("get collection flow failed")
            return 60612, "get collection flow failed"
        flow = collection.find_one({"merchant_identity": merchant_identity, "deleted": 0})
        if not flow:
            g_log.error("retrieve flow failed")
            return 60613, "retrieve failed"
        balance = flow["balance"]

        collection2 = get_mongo_collection("parameters")
        if not collection2:
            g_log.error("get collection parameters failed")
            return 60614, "get collection parameters failed"
        parameters = collection2.find_one({"merchant_identity": merchant_identity, "deleted": 0})
        if not parameters:
            g_log.error("retrieve parameters failed")
            return 60615, "retrieve failed"
        balance_ratio = parameters["balance_ratio"]

        g_log.debug("balance / ratio = %d / %d", balance, balance_ratio)
        return 60600,  float('%.2f' % (balance / float(balance_ratio)))
    except Exception as e:
        g_log.error("%s", e)
        return 60616, "exception"


def generate_trade_no(numbers, merchant, money, t):
    """
    生成交易订单号  trade_no = md5(numbers, merchant, money, time)
    :param numbers:
    :param merchant:
    :param money:
    :param t: since January 1, 1970
    :return:
    """
    trade_no = '%s%s%s%s' % (numbers, merchant, money, time.mktime(t.timetuple()))
    m = hashlib.md5()
    m.update(trade_no)
    trade_no = m.hexdigest()
    return trade_no


def recharge_trade_no(**kwargs):
    """
    获取充值订单号，未认证商家不允许操作
    :param kwargs: {"numbers": 118688982240, "merchant_identity": "", "money": 100}
    :return: (60300, "yes")/成功，(>60300, "errmsg")/失败
    """
    try:
        # 检查要请求用户numbers必须是平台管理员
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_merchant(numbers):
            g_log.warning("not manager %s", numbers)
            return 60711, "not manager"

        # 检查管理员和商家关系
        merchant_identity = kwargs.get("merchant_identity", "")
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 60712, "not manager"

        # 认证用户才可以充值
        if not merchant_is_verified(merchant_identity):
            g_log.error("merchant %s not verified", merchant_identity)
            return 60713, "not verified"

        money = kwargs.get("money", 0)
        # 生成唯一订单号
        now = datetime.now()
        trade_no = generate_trade_no(numbers, merchant_identity, money, now)
        g_log.debug("generate trade number: %s", trade_no)

        # 更新记录入库
        collection = get_mongo_collection("trade_no")
        if not collection:
            g_log.error("get collection trade_no failed")
            return 60715, "get collection trade_no failed"
        result = collection.insert_one({"merchant_identity": merchant_identity, "time": now, "state": "pending",
                                        "operator": numbers, "money": money, "trade_no": trade_no})
        if not result:
            g_log.error("insert trade_no failed")
            return 60716, "insert trade_no failed"
        return 60700, trade_no
    except Exception as e:
        g_log.error("%s", e)
        return 60717, "exception"


def alipay_async_notify(notify):
    """
    获取充值订单号，未认证商家不允许操作
    :param kwargs: {"numbers": 118688982240, "merchant_identity": "", "money": 100}
    :return: (60300, "yes")/成功，(>60300, "errmsg")/失败
    """
    try:
        trade_status = notify.trade_status
        sign_type = notify.sign_type
        sign = notify.sign
        notify_type = notify.notify_type
        notify_id = notify.notify_id
        buyer_id = notify.buyer_id
        buyer_email = notify.buyer_email
        out_trade_no = notify.out_trade_no
        trade_no = notify.trade_no
        seller_email = notify.seller_email
        seller_id = notify.seller_id
        total_fee = notify.total_fee
        notify_time = notify.notify_time
        gmt_create = notify.gmt_create
        gmt_payment = notify.gmt_payment

        # 验证签名 level1 处理，这里只检查签名类型
        if sign_type.upper() != "RSA":
            g_log.error("illegal sign type %s", sign_type)
            return 60811, "invalid notify"

        # 验证是否是支付宝发来的通知，暂时不处理，同步https请求影响性能，TODO  异步http
        # if notify_type.lower() != "trade_status_sync":
        #     g_log.error("illegal notify type %s", notify_type)
        #     return 60812, "invalid notify"
        # conn = httplib.HTTPSConnection("mapi.alipay.com")
        # url = "/gateway.do?service=notify_verify&partner=2088221780225801&notify_id=%s" % notify_id
        # g_log.debug("check notify referrer, https://mapi.alipay.com%s", url)
        # conn.request("GET", url)
        # res = conn.getresponse()
        # if res.status == 200 and res.reason == "OK" and res.read() == "true":
        #     g_log.debug("notify from alipay")
        # else:
        #     g_log.error("invalid notify, not from alipay")
        #     return 60813, "invalid notify"

        # 验证商家支付宝账号
        if seller_email != "biiyooit@qq.com":
            g_log.error("illegal seller email %s or seller id %s", seller_email, seller_id)
            return 60814, "invalid notify"

        # 验证是否为商户系统中创建的订单号
        collection = get_mongo_collection("trade_no")
        if not collection:
            g_log.error("get collection trade_no failed")
            return 60815, "get collection trade_no failed"
        if "TRADE_FINISHED" == trade_status or "TRADE_SUCCESS" == trade_status:
            state = "done"
        elif "WAIT_BUYER_PAY" == trade_status:
            state = "wait"
        else:
            state = "close"
        # result = collection.find_one({"trade_no": out_trade_no, "money": total_fee})
        result = collection.find_one_and_update({"trade_no": out_trade_no, "money": total_fee, "state": "pending"},
        # result = collection.find_one_and_update({"trade_no": out_trade_no},
                                                {"$set": {"state": state}})
        if not result:
            g_log.error("invalid notify, trade number not match")
            return 60816, "invalid notify"
        merchant = result["merchant_identity"]

        # 通知入库
        collection = get_mongo_collection("alipay_notify")
        if not collection:
            g_log.error("get collection alipay_notify failed")
            return 60817, "get collection alipay_notify failed"
        result = collection.insert_one({"trade_no": trade_no, "buyer_id": buyer_id, "buyer_email": buyer_email,
                                        "out_trade_no": out_trade_no, "total_fee": total_fee, "gmt_create": gmt_create,
                                        "gmt_payment": gmt_payment, "notify_time": notify_time})
        if not result:
            g_log.error("insert alipay_notify failed")
            return 60818, "insert alipay_notify failed"

        # 更新商家支付宝信息
        code, message = merchant_update_alipay(merchant, buyer_email, buyer_id)
        if 30400 != code:
            g_log.warning("update merchant alipay account failed")

        return 60800, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 60819, "exception"


def merchant_flow_copy_from_document(material, value):
    g_log.debug("yes")
    g_log.debug(value["balance"])
    material.upper_bound = int(value["upper_bound"])
    # material.may_issued = int(value["may_issued"])
    material.may_issued = int(value["upper_bound"]) - int(value["issued"])
    material.issued = int(value["issued"])
    # material.interchange_in = int(value["interchange_in"])
    # material.interchange_out = int(value["interchange_out"])
    # material.interchange_consumption = int(value["interchange_consumption"])
    # material.consumption = int(value["consumption"])
    material.balance = int(value["balance"])
    material.identity = str(value["_id"])


def balance_record_copy_from_document(material, value):
    material.operator = value["operator"]
    material.time = value["time"].strftime("%Y-%m-%d %H:%M:%S")
    material.money = value["money"]
    material.identity = str(value["_id"])
    material.direction = value["type"]
    # material.balance = value["balance"]


# 测试时mongo_connection的配置文件路径写全
if "__main__" == __name__:
    kwargs1 = {"numbers": "118688982240", "merchant_identity": "562c7ad6494ac55faf750798", "bond": 100}
    upper_bound_update(**kwargs1)
    kwargs1 = {"numbers": "118688982240", "merchant_identity": "562c7ad6494ac55faf750798", "supplement": 1002}
    for mode1 in ["may_issued", "issued", "interchange_in", "interchange_out", "interchange_consumption"]:
        kwargs1["mode"] = mode1
        merchant_credit_update(**kwargs1)
