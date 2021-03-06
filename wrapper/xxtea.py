# -*- coding: utf-8 -*-
__author__ = 'Ma Bingya'

############################################################
#                                                          #  
# The implementation of PHPRPC Protocol 3.0                #  
#                                                          #  
# xxtea.py                                                 #  
#                                                          #  
# Release 3.0.0                                            #  
# Copyright (c) 2005-2008 by Team-PHPRPC                   #  
#                                                          #  
# WebSite:  http://www.phprpc.org/                         #  
#           http://www.phprpc.net/                         #  
#           http://www.phprpc.com/                         #  
#           http://sourceforge.net/projects/php-rpc/       #  
#                                                          #  
# Authors:  Ma Bingyao <andot@ujn.edu.cn>                  #  
#                                                          #  
# This file may be distributed and/or modified under the   #  
# terms of the GNU Lesser General Public License (LGPL)    #  
# version 3.0 as published by the Free Software Foundation #  
# and appearing in the included file LICENSE.              #  
#                                                          #  
############################################################
#  
# XXTEA encryption arithmetic library.  
#  
# Copyright (C) 2005-2008 Ma Bingyao <andot@ujn.edu.cn>  
# Version: 1.0  
# LastModified: Oct 5, 2008  
# This library is free.  You can redistribute it and/or modify it.  

import struct  
  
_DELTA = 0x9E3779B9


def _long2str(v, w):  
    n = (len(v) - 1) << 2  
    if w:
        m = v[-1]  
        if (m < n - 3) or (m > n):
            return ''
        n = m
    s = struct.pack('<%iL' % len(v), *v)  
    return s[0:n] if w else s  


def _str2long(s, w):  
    n = len(s)  
    m = (4 - (n & 3) & 3) + n  
    s = s.ljust(m, "\0")  
    v = list(struct.unpack('<%iL' % (m >> 2), s))  
    if w:
        v.append(n)
    return v  


def encrypt(plain, key):
    if plain == '':
        return plain
    v = _str2long(plain, True)
    k = _str2long(key.ljust(16, "\0"), False)  
    n = len(v) - 1  
    z = v[n]  
    y = v[0]  
    s = 0
    q = 6 + 52 // (n + 1)  
    while q > 0:  
        s = (s + _DELTA) & 0xffffffff  
        e = s >> 2 & 3  
        for p in xrange(n):  
            y = v[p + 1]  
            v[p] = (v[p] + ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (s ^ y) + (k[p & 3 ^ e] ^ z))) & 0xffffffff  
            z = v[p]  
        y = v[0]  
        v[n] = (v[n] + ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (s ^ y) + (k[n & 3 ^ e] ^ z))) & 0xffffffff  
        z = v[n]  
        q -= 1  
    return _long2str(v, False)  


def decrypt(cipher, key):
    if cipher == '':
        return cipher
    v = _str2long(cipher, False)
    k = _str2long(key.ljust(16, "\0"), False)  
    n = len(v) - 1  
    z = v[n]  
    y = v[0]  
    q = 6 + 52 // (n + 1)  
    s = (q * _DELTA) & 0xffffffff  
    while s != 0:
        e = s >> 2 & 3  
        for p in xrange(n, 0, -1):  
            z = v[p - 1]  
            v[p] = (v[p] - ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (s ^ y) + (k[p & 3 ^ e] ^ z))) & 0xffffffff  
            y = v[p]  
        z = v[n]  
        v[0] = (v[0] - ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (s ^ y) + (k[0 & 3 ^ e] ^ z))) & 0xffffffff  
        y = v[0]  
        s = (s - _DELTA) & 0xffffffff  
    return _long2str(v, True)  


if __name__ == "__main__":  
    print decrypt(encrypt('Hello World!', 'key'), 'key')