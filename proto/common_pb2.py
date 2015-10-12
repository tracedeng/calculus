# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: common.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import register_pb2 as register__pb2
import vip_pb2 as vip__pb2
import consumer_pb2 as consumer__pb2
import merchant_pb2 as merchant__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='common.proto',
  package='',
  syntax='proto3',
  serialized_pb=b'\n\x0c\x63ommon.proto\x1a\x0eregister.proto\x1a\tvip.proto\x1a\x0e\x63onsumer.proto\x1a\x0emerchant.proto\"\xd1\x05\n\x07Request\x12\x1a\n\x04head\x18\x01 \x01(\x0b\x32\x0c.RequestHead\x12*\n\x10register_request\x18\x02 \x01(\x0b\x32\x10.RegisterRequest\x12\x37\n\x17\x63onsumer_create_request\x18\x64 \x01(\x0b\x32\x16.ConsumerCreateRequest\x12;\n\x19\x63onsumer_retrieve_request\x18\x65 \x01(\x0b\x32\x18.ConsumerRetrieveRequest\x12\x46\n\x1f\x63onsumer_batch_retrieve_request\x18\x66 \x01(\x0b\x32\x1d.ConsumerBatchRetrieveRequest\x12\x37\n\x17\x63onsumer_update_request\x18g \x01(\x0b\x32\x16.ConsumerUpdateRequest\x12\x37\n\x17\x63onsumer_delete_request\x18h \x01(\x0b\x32\x16.ConsumerDeleteRequest\x12\x38\n\x17merchant_create_request\x18\xc8\x01 \x01(\x0b\x32\x16.MerchantCreateRequest\x12<\n\x19merchant_retrieve_request\x18\xc9\x01 \x01(\x0b\x32\x18.MerchantRetrieveRequest\x12G\n\x1fmerchant_batch_retrieve_request\x18\xca\x01 \x01(\x0b\x32\x1d.MerchantBatchRetrieveRequest\x12\x38\n\x17merchant_update_request\x18\xcb\x01 \x01(\x0b\x32\x16.MerchantUpdateRequest\x12\x38\n\x17merchant_delete_request\x18\xcc\x01 \x01(\x0b\x32\x16.MerchantDeleteRequest\x12\x19\n\x03vip\x18\x90N \x01(\x0b\x32\x0b.VipRequest\"\xea\x05\n\x08Response\x12\x1b\n\x04head\x18\x01 \x01(\x0b\x32\r.ResponseHead\x12,\n\x11register_response\x18\x02 \x01(\x0b\x32\x11.RegisterResponse\x12\x39\n\x18\x63onsumer_create_response\x18\x64 \x01(\x0b\x32\x17.ConsumerCreateResponse\x12=\n\x1a\x63onsumer_retrieve_response\x18\x65 \x01(\x0b\x32\x19.ConsumerRetrieveResponse\x12H\n consumer_batch_retrieve_response\x18\x66 \x01(\x0b\x32\x1e.ConsumerBatchRetrieveResponse\x12\x39\n\x18\x63onsumer_update_response\x18g \x01(\x0b\x32\x17.ConsumerUpdateResponse\x12\x39\n\x18\x63onsumer_delete_response\x18h \x01(\x0b\x32\x17.ConsumerDeleteResponse\x12:\n\x18merchant_create_response\x18\xc8\x01 \x01(\x0b\x32\x17.MerchantCreateResponse\x12>\n\x1amerchant_retrieve_response\x18\xc9\x01 \x01(\x0b\x32\x19.MerchantRetrieveResponse\x12I\n merchant_batch_retrieve_response\x18\xca\x01 \x01(\x0b\x32\x1e.MerchantBatchRetrieveResponse\x12:\n\x18merchant_update_response\x18\xcb\x01 \x01(\x0b\x32\x17.MerchantUpdateResponse\x12:\n\x18merchant_delete_response\x18\xcc\x01 \x01(\x0b\x32\x17.MerchantDeleteResponse\x12\x1a\n\x03vip\x18\x90N \x01(\x0b\x32\x0c.VipResponse\"j\n\x0bRequestHead\x12\x0b\n\x03\x63md\x18\x01 \x01(\r\x12\x0b\n\x03seq\x18\x02 \x01(\x04\x12\x14\n\x0cphone_number\x18\x03 \x01(\t\x12\x13\n\x0bsession_key\x18\x04 \x01(\t\x12\x16\n\x0e\x63oroutine_uuid\x18\x05 \x01(\t\"G\n\x0cResponseHead\x12\x0b\n\x03\x63md\x18\x01 \x01(\r\x12\x0b\n\x03seq\x18\x02 \x01(\x04\x12\x0c\n\x04\x63ode\x18\x03 \x01(\x05\x12\x0f\n\x07message\x18\x04 \x01(\tb\x06proto3'
  ,
  dependencies=[register__pb2.DESCRIPTOR,vip__pb2.DESCRIPTOR,consumer__pb2.DESCRIPTOR,merchant__pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_REQUEST = _descriptor.Descriptor(
  name='Request',
  full_name='Request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='head', full_name='Request.head', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='register_request', full_name='Request.register_request', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_create_request', full_name='Request.consumer_create_request', index=2,
      number=100, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_retrieve_request', full_name='Request.consumer_retrieve_request', index=3,
      number=101, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_batch_retrieve_request', full_name='Request.consumer_batch_retrieve_request', index=4,
      number=102, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_update_request', full_name='Request.consumer_update_request', index=5,
      number=103, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_delete_request', full_name='Request.consumer_delete_request', index=6,
      number=104, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_create_request', full_name='Request.merchant_create_request', index=7,
      number=200, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_retrieve_request', full_name='Request.merchant_retrieve_request', index=8,
      number=201, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_batch_retrieve_request', full_name='Request.merchant_batch_retrieve_request', index=9,
      number=202, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_update_request', full_name='Request.merchant_update_request', index=10,
      number=203, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_delete_request', full_name='Request.merchant_delete_request', index=11,
      number=204, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='vip', full_name='Request.vip', index=12,
      number=10000, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=76,
  serialized_end=797,
)


_RESPONSE = _descriptor.Descriptor(
  name='Response',
  full_name='Response',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='head', full_name='Response.head', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='register_response', full_name='Response.register_response', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_create_response', full_name='Response.consumer_create_response', index=2,
      number=100, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_retrieve_response', full_name='Response.consumer_retrieve_response', index=3,
      number=101, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_batch_retrieve_response', full_name='Response.consumer_batch_retrieve_response', index=4,
      number=102, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_update_response', full_name='Response.consumer_update_response', index=5,
      number=103, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='consumer_delete_response', full_name='Response.consumer_delete_response', index=6,
      number=104, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_create_response', full_name='Response.merchant_create_response', index=7,
      number=200, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_retrieve_response', full_name='Response.merchant_retrieve_response', index=8,
      number=201, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_batch_retrieve_response', full_name='Response.merchant_batch_retrieve_response', index=9,
      number=202, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_update_response', full_name='Response.merchant_update_response', index=10,
      number=203, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='merchant_delete_response', full_name='Response.merchant_delete_response', index=11,
      number=204, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='vip', full_name='Response.vip', index=12,
      number=10000, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=800,
  serialized_end=1546,
)


_REQUESTHEAD = _descriptor.Descriptor(
  name='RequestHead',
  full_name='RequestHead',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cmd', full_name='RequestHead.cmd', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='seq', full_name='RequestHead.seq', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='phone_number', full_name='RequestHead.phone_number', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='session_key', full_name='RequestHead.session_key', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='coroutine_uuid', full_name='RequestHead.coroutine_uuid', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1548,
  serialized_end=1654,
)


_RESPONSEHEAD = _descriptor.Descriptor(
  name='ResponseHead',
  full_name='ResponseHead',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cmd', full_name='ResponseHead.cmd', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='seq', full_name='ResponseHead.seq', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='code', full_name='ResponseHead.code', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='ResponseHead.message', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1656,
  serialized_end=1727,
)

_REQUEST.fields_by_name['head'].message_type = _REQUESTHEAD
_REQUEST.fields_by_name['register_request'].message_type = register__pb2._REGISTERREQUEST
_REQUEST.fields_by_name['consumer_create_request'].message_type = consumer__pb2._CONSUMERCREATEREQUEST
_REQUEST.fields_by_name['consumer_retrieve_request'].message_type = consumer__pb2._CONSUMERRETRIEVEREQUEST
_REQUEST.fields_by_name['consumer_batch_retrieve_request'].message_type = consumer__pb2._CONSUMERBATCHRETRIEVEREQUEST
_REQUEST.fields_by_name['consumer_update_request'].message_type = consumer__pb2._CONSUMERUPDATEREQUEST
_REQUEST.fields_by_name['consumer_delete_request'].message_type = consumer__pb2._CONSUMERDELETEREQUEST
_REQUEST.fields_by_name['merchant_create_request'].message_type = merchant__pb2._MERCHANTCREATEREQUEST
_REQUEST.fields_by_name['merchant_retrieve_request'].message_type = merchant__pb2._MERCHANTRETRIEVEREQUEST
_REQUEST.fields_by_name['merchant_batch_retrieve_request'].message_type = merchant__pb2._MERCHANTBATCHRETRIEVEREQUEST
_REQUEST.fields_by_name['merchant_update_request'].message_type = merchant__pb2._MERCHANTUPDATEREQUEST
_REQUEST.fields_by_name['merchant_delete_request'].message_type = merchant__pb2._MERCHANTDELETEREQUEST
_REQUEST.fields_by_name['vip'].message_type = vip__pb2._VIPREQUEST
_RESPONSE.fields_by_name['head'].message_type = _RESPONSEHEAD
_RESPONSE.fields_by_name['register_response'].message_type = register__pb2._REGISTERRESPONSE
_RESPONSE.fields_by_name['consumer_create_response'].message_type = consumer__pb2._CONSUMERCREATERESPONSE
_RESPONSE.fields_by_name['consumer_retrieve_response'].message_type = consumer__pb2._CONSUMERRETRIEVERESPONSE
_RESPONSE.fields_by_name['consumer_batch_retrieve_response'].message_type = consumer__pb2._CONSUMERBATCHRETRIEVERESPONSE
_RESPONSE.fields_by_name['consumer_update_response'].message_type = consumer__pb2._CONSUMERUPDATERESPONSE
_RESPONSE.fields_by_name['consumer_delete_response'].message_type = consumer__pb2._CONSUMERDELETERESPONSE
_RESPONSE.fields_by_name['merchant_create_response'].message_type = merchant__pb2._MERCHANTCREATERESPONSE
_RESPONSE.fields_by_name['merchant_retrieve_response'].message_type = merchant__pb2._MERCHANTRETRIEVERESPONSE
_RESPONSE.fields_by_name['merchant_batch_retrieve_response'].message_type = merchant__pb2._MERCHANTBATCHRETRIEVERESPONSE
_RESPONSE.fields_by_name['merchant_update_response'].message_type = merchant__pb2._MERCHANTUPDATERESPONSE
_RESPONSE.fields_by_name['merchant_delete_response'].message_type = merchant__pb2._MERCHANTDELETERESPONSE
_RESPONSE.fields_by_name['vip'].message_type = vip__pb2._VIPRESPONSE
DESCRIPTOR.message_types_by_name['Request'] = _REQUEST
DESCRIPTOR.message_types_by_name['Response'] = _RESPONSE
DESCRIPTOR.message_types_by_name['RequestHead'] = _REQUESTHEAD
DESCRIPTOR.message_types_by_name['ResponseHead'] = _RESPONSEHEAD

Request = _reflection.GeneratedProtocolMessageType('Request', (_message.Message,), dict(
  DESCRIPTOR = _REQUEST,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:Request)
  ))
_sym_db.RegisterMessage(Request)

Response = _reflection.GeneratedProtocolMessageType('Response', (_message.Message,), dict(
  DESCRIPTOR = _RESPONSE,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:Response)
  ))
_sym_db.RegisterMessage(Response)

RequestHead = _reflection.GeneratedProtocolMessageType('RequestHead', (_message.Message,), dict(
  DESCRIPTOR = _REQUESTHEAD,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:RequestHead)
  ))
_sym_db.RegisterMessage(RequestHead)

ResponseHead = _reflection.GeneratedProtocolMessageType('ResponseHead', (_message.Message,), dict(
  DESCRIPTOR = _RESPONSEHEAD,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:ResponseHead)
  ))
_sym_db.RegisterMessage(ResponseHead)


# @@protoc_insertion_point(module_scope)
