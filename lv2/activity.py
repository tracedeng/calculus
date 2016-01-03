# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from datetime import datetime
from pymongo.collection import ReturnDocument
from mongo_connection import get_mongo_collection
import common_pb2
import package
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from account_valid import account_is_valid_merchant
from account_auxiliary import identity_to_numbers, verify_session_key
from merchant import user_is_merchant_manager
from google_bug import message_has_field


class Activity():
    """
    活动模块，命令号<700
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
            # 验证登录态，某些命令可能不需要登录态，此处做判断
            code, message = verify_session_key(self.numbers, self.session_key)
            if 10400 != code:
                g_log.debug("verify session key failed, %s, %s", code, message)
                return package.error_response(self.cmd, self.seq, 70001, "invalid session key")

            command_handle = {701: self.activity_create, 702: self.activity_retrieve, 703: self.activity_batch_retrieve,
                              704: self.activity_update, 705: self.activity_delete}
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

    def activity_create(self):
        """
        创建activity资料
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.activity_create_request
            numbers = body.numbers
            identity = body.identity
            activity_identity = body.activity_identity
            material = body.material

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 70101
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要创建的用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to create activity %s", self.numbers, numbers)
                self.code = 70102
                self.message = "no privilege to create activity"
                return 1

            kwargs = {"numbers": numbers, "title": material.title, "poster": material.poster, "credit": material.credit,
                      "introduce": material.introduce, "activity_identity": activity_identity}
            g_log.debug("create activity: %s", kwargs)
            self.code, self.message = activity_create(**kwargs)

            if 70100 == self.code:
                # 创建成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "create activity done"
                
                response.activity_create_response.identity = self.message
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def activity_retrieve(self):
        """
        获取activity资料
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.activity_retrieve_request
            numbers = body.numbers
            identity = body.identity
            activity_identity = body.activity_identity
            
            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 70201
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要获取的用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to retrieve activity %s", self.numbers, numbers)
                self.code = 70202
                self.message = "no privilege to retrieve activity"
                return 1

            self.code, self.message = activity_retrieve_with_numbers(numbers, activity_identity)

            if 70200 == self.code:
                # 获取成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "retrieve activity done"

                materials = response.activity_retrieve_response.materials
                for value in self.message:
                    material = materials.add()
                    activity_material_copy_from_document(material, value)

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0
        
    def activity_update(self):
        """
        修改activity资料
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.activity_update_request
            numbers = body.numbers
            identity = body.identity
            merchant_identity = body.merchant_identity
            activity_identity = body.activity_identity
            material = body.material

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    self.code = 70301
                    self.message = "missing argument"
                    return 1

            # 发起请求的商家和要创建的商家不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to update activity %s", self.numbers, numbers)
                self.code = 70302
                self.message = "no privilege to update activity"
                return 1

            value = {}

            if message_has_field(material, "title"):
                value["title"] = material.title
            if message_has_field(material, "poster"):
                value["poster"] = material.poster
            if message_has_field(material, "introduce"):
                value["introduce"] = material.introduce
            if message_has_field(material, "credit"):
                value["credit"] = material.credit
            if message_has_field(material, "expire_time"):
                value["expire_time"] = material.expire_time

            value["merchant_identity"] = merchant_identity
            value["activity_identity"] = activity_identity
            g_log.debug("update activity material: %s", value)
            self.code, self.message = activity_update_with_numbers(numbers, **value)

            if 70300 == self.code:
                # 更新成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "update activity material done"
                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0

    def activity_delete(self):
        """
        删除活动资料
        :return: 0/不回包给前端，pb/正确返回，1/错误，并回错误包
        """
        try:
            body = self.request.activity_delete_request
            numbers = body.numbers
            identity = body.identity
            merchant_identity = body.merchant_identity
            activity_identity = body.activity_identity

            if not numbers:
                # 根据包体中的identity获取numbers
                code, numbers = identity_to_numbers(identity)
                if code != 10500:
                    g_log.debug("missing argument numbers")
                    self.code = 70401
                    self.message = "missing argument"
                    return 1

            # 发起请求的用户和要创建的用户不同，认为没有权限，TODO...更精细控制
            if self.numbers != numbers:
                g_log.warning("%s no privilege to delete activity %s", self.numbers, numbers)
                self.code = 70402
                self.message = "no privilege to delete activity"
                return 1

            self.code, self.message = activity_delete_with_numbers(numbers, merchant_identity, activity_identity)

            if 70400 == self.code:
                # 删除成功
                response = common_pb2.Response()
                response.head.cmd = self.head.cmd
                response.head.seq = self.head.seq
                response.head.code = 1
                response.head.message = "delete activity done"

                return response
            else:
                return 1
        except Exception as e:
            g_log.error("%s", e)
            return 0


def enter(request):
    """
    活动模块入口
    :param request: 解析后的pb格式
    :return: 0/不回包给前端，pb/正确返回，timeout/超时
    """
    try:
        activity = Activity(request)
        return activity.enter()
    except Exception as e:
        g_log.error("%s", e)
        return 0


# pragma 增加活动API
def activity_create(**kwargs):
    """
    新增活动
    :param kwargs: {"numbers": "18688982240", "title": "good taste", "introduce": "ego cogito ergo sum",
                    "poster": "a/18688982240/x87cd", "credit": 100, "activity_identity": "xij923f0a8m"}
    :return: (70100, "yes")/成功，(>70100, "errmsg")/失败
    """
    try:
        # 检查要创建的用户numbers
        numbers = kwargs.get("numbers", "")
        if not account_is_valid_merchant(numbers):
            g_log.warning("not manager %s", numbers)
            return 70111, "not manager"

        activity_identity = kwargs.get("activity_identity", "")
        activity = user_is_merchant_manager(numbers, activity_identity)
        if not activity:
            g_log.error("%s is not activity %s manager", numbers, activity_identity)
            return 70112, "not manager"

        # 活动标题不能超过32字节，超过要截取前32字节
        title = kwargs.get("title", "")
        if len(title) > 32:
            g_log.warning("too long title %s", title)
            title = title[0:32]

        # 活动介绍不能超过512字节，超过要截取前512字节
        introduce = kwargs.get("introduce", "")
        if len(introduce) > 512:
            g_log.warning("too long introduce %s", introduce)
            introduce = introduce[0:512]

        poster = kwargs.get("poster", "")
        credit = kwargs.get("credit", 0)

        value = {"numbers": numbers, "title": title, "introduce": introduce, "introduce": introduce, "credit": credit,
                 "activity_identity": activity_identity, "poster": poster, "deleted": 0, "create_time": datetime.now(),
                 "expire_time": datetime.now()}

        # 存入数据库
        collection = get_mongo_collection("activity")
        if not collection:
            g_log.error("get collection activity failed")
            return 70113, "get collection activity failed"
        activity = collection.find_one_and_replace({"numbers": numbers}, value, upsert=True,
                                                   return_document=ReturnDocument.AFTER)
        if not activity:
            g_log.error("create activity %s failed", numbers)
            return 70114, "create activity failed"

        return 70100, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 70115, "exception"
    
    
# pragma 读取活动资料API
def activity_retrieve_with_numbers(numbers, merchant_identity):
    """
    读取活动资料
    :param numbers: 用户电话号码
    :return: (70200, activity)/成功，(>70200, "errmsg")/失败
    """
    try:
        # 检查合法账号
        if not account_is_valid_merchant(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 70211, "invalid account"

        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not activity %s manager", numbers, merchant_identity)
            return 70212, "not manager"

        collection = get_mongo_collection("activity")
        if not collection:
            g_log.error("get collection activity failed")
            return 70213, "get collection activity failed"
        activity = collection.find_one({"merchant_identity": merchant_identity, "deleted": 0})
        if not activity:
            g_log.debug("activity %s not exist", numbers)
            return 70214, "activity not exist"

        return 70200, activity
    except Exception as e:
        g_log.error("%s", e)
        return 70215, "exception"


def activity_retrieve_with_identity(identity, activity_identity):
    """
    查询活动资料
    :param identity: 用户ID
    :return:
    """
    try:
        # 根据用户id查找用户电话号码
        code, numbers = identity_to_numbers(identity)
        if code != 10500:
            return 70216, "illegal identity"
        return activity_retrieve_with_numbers(numbers)
    except Exception as e:
        g_log.error("%s", e)
        return 70217, "exception"


def activity_retrieve(activity_identity, numbers=None, identity=None):
    """
    获取活动资料，用户电话号码优先
    :param numbers: 用户电话号码
    :param identity: 用户ID
    :return:
    """
    try:
        if numbers:
            return activity_retrieve_with_numbers(numbers, activity_identity)
        elif identity:
            return activity_retrieve_with_identity(identity, activity_identity)
        else:
            return 70218, "bad arguments"
    except Exception as e:
        g_log.error("%s", e)
        return 70219, "exception"


# pragma 更新活动资料API
def activity_update_with_numbers(numbers, **kwargs):
    """
    更新活动资料
    :param numbers: 用户电话号码
    :param kwargs: {"numbers": "18688982240", "title": "good taste", "introduce": "ego cogito ergo sum",
                    "poster": "a/18688982240/x87cd", "credit": 100, "activity_identity": "xij923f0a8m"}
    :return: (20400, "yes")/成功，(>20400, "errmsg")/失败
    """
    try:
        # 检查合法账号
        if not account_is_valid_merchant(numbers):
            g_log.warning("invalid merchant account %s", numbers)
            return 70311, "invalid phone number"

        merchant_identity = kwargs.get("merchant_identity")
        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 70312, "not manager"
        activity_identity = kwargs.get("activity_identity")

        value = {}
        # 标题不能超过32字节，超过要截取前32字节
        title = kwargs.get("title")
        if title:
            if len(title) > 32:
                g_log.warning("too long nickname %s", title)
                title = title[0:32]
            value["title"] = title

        credit = kwargs.get("credit", 0)
        if credit:
            value["credit"] = credit

        # 活动介绍不能超过512字节，超过要截取前512字节
        introduce = kwargs.get("introduce")
        if introduce:
            if len(introduce) > 512:
                g_log.warning("too long introduce %s", introduce)
                introduce = introduce[0:512]
            value["introduce"] = introduce

        # TODO...检查
        poster = kwargs.get("poster")
        if poster:
            value["poster"] = poster

        g_log.debug("update activity material: %s", value)
        # 存入数据库
        collection = get_mongo_collection("activity")
        if not collection:
            g_log.error("get collection activity failed")
            return 70313, "get collection activity failed"
        activity = collection.find_one_and_update({"merchant_identity": merchant_identity,
                                                   "identity": activity_identity, "deleted": 0}, {"$set": value})
        if not activity:
            g_log.error("activity %s exist", numbers)
            return 70314, "activity not exist"
        return 70300, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 70315, "exception"


# pragma 删除活动资料API
def activity_delete_with_numbers(numbers, merchant_identity, activity_identity):
    """
    删除活动资料
    :param numbers: 用户电话号码
    :return: (70400, "yes")/成功，(>70400, "errmsg")/失败
    """
    try:
        # 检查合法账号
        if not account_is_valid_merchant(numbers):
            g_log.warning("invalid customer account %s", numbers)
            return 70411, "invalid phone number"

        merchant = user_is_merchant_manager(numbers, merchant_identity)
        if not merchant:
            g_log.error("%s is not merchant %s manager", numbers, merchant_identity)
            return 70412, "not manager"

        collection = get_mongo_collection("activity")
        if not collection:
            g_log.error("get collection activity failed")
            return 70413, "get collection activity failed"
        activity = collection.find_one_and_update({"merchant_identity": merchant_identity,
                                                   "activity_identity": activity_identity, "deleted": 0},
                                                  {"$set": {"deleted": 1}})
        if not activity:
            g_log.error("activity %s not exist", numbers)
            return 70414, "activity not exist"
        return 70400, "yes"
    except Exception as e:
        g_log.error("%s", e)
        return 70415, "exception"


def activity_material_copy_from_document(material, value):
    material.numbers = value["numbers"]
    material.identity = str(value["_id"])
    
    material.credit = int(value["credit"])
    material.introduce = value["introduce"]
    material.title = value["title"]
    material.poster = value["poster"]
    material.create_time = value["create_time"].strftime("%Y-%m-%d %H:%M:%S")
    material.expire_time = value["expire_time"].strftime("%Y-%m-%d %H:%M:%S")