#!/usr/bin/py3.8
# -*- coding:utf-8 -*-
from requests import get, post, session
from random import sample
from requests.exceptions import Timeout, ReadTimeout, ConnectionError
import re
import time
import yaml
import sys
from gotify import gotify
from _datetime import datetime, timedelta, timezone

host = 'http://yy.lib.neau.edu.cn/dgyy/'
header_post = {
    'Host': 'yy.lib.neau.edu.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'http://yy.lib.neau.edu.cn',
    'Referer': 'http://yy.lib.neau.edu.cn/dgyy/'
}
header_get = {
    'Host': 'yy.lib.neau.edu.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Type': 'application/x-www-form-urlencoded'
}
proxy = {
    "http": "http://127.0.0.1:8080"
}
body = {
    '__EVENTTARGET':'ctl00$MainContent$Calendar1',
    '__EVENTARGUMENT':'',
    '__VIEWSTATE':'',
    '__VIEWSTATEGENERATOR':'',
    '__EVENTVALIDATION':'',
    'ctl00$MainContent$TextBox1':'',
    'ctl00$MainContent$TextBox2':'',
    'ctl00$MainContent$TextBox3':'',
    'ctl00$MainContent$TextBox4':'',
}
CONNECTION_TIME_OUT = 5
READ_TIME_OUT = 10

# 读取yml配置
def getYmlConfig(yaml_file):
    file = open(yaml_file, 'r', encoding="utf-8")
    file_data = file.read()
    file.close()
    config = yaml.load(file_data, Loader=yaml.FullLoader)
    return dict(config)

# 全局配置
config = getYmlConfig(yaml_file=sys.argv[1])

def getTimeStr():
    utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    return bj_dt.strftime("%Y-%m-%d %H:%M:%S")

def randomSession(x):
    return ''.join(sample('1234567890zyxwvutsrqponmlkjihgfedcba', x))

def setCookie(ori_cookie):
    cookie_tmp = session()
    for key, value in ori_cookie.items():
        cookie_tmp.cookies.set(key, value)
    return cookie_tmp.cookies

def POST(url, cookie, debug, data={}):
    if(debug == 1):
        return post(url, headers=header_post, data=data, cookies=cookie, timeout=(CONNECTION_TIME_OUT, READ_TIME_OUT), proxies=proxy)
    else:
        return post(url, headers=header_post, data=data, cookies=cookie, timeout=(CONNECTION_TIME_OUT, READ_TIME_OUT))


def GET(url, cookie, debug, data={}):
    if(debug == 1):
        return get(url, headers=header_get, data=data, cookies=cookie, timeout=(CONNECTION_TIME_OUT, READ_TIME_OUT), proxies=proxy)
    else:
        return get(url, headers=header_get, data=data, cookies=cookie, timeout=(CONNECTION_TIME_OUT, READ_TIME_OUT))

def getHidden(res):
    global body
    con = res.content.decode('utf-8','ignore')
    body['__VIEWSTATE'] =re.findall(r'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="(.*?)" />', con,re.I)[0]
    body['__EVENTVALIDATION'] =re.findall(r'input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*?)" />', con,re.I)[0]
    body['__VIEWSTATEGENERATOR'] =re.findall(r'input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*?)" />', con,re.I)[0]
    body['__EVENTARGUMENT'] =int(re.findall(r"javascript:__doPostBack\(\'ctl00\$MainContent\$Calendar1\',\'(.*)\'\)", con,re.I)[1])+1

def chooseMode(choice):
    if choice == 1:
        body['ctl00$MainContent$YuYueYuebtn'] = "我的预约"
    elif choice == 2:
        body['ctl00$MainContent$QXYY'] = "取消预约"
    elif choice == 3:
        body['ctl00$MainContent$YuYue'] = "预约"

# debug_mode = int(input("127.0.0.1:8080代理模式(0/1)【不清楚有什么用的请选0】："))
debug_mode = 0
vpncookie = {"__AntiXsrfToken": randomSession(32)}
cookie = setCookie(vpncookie)

try:
    res = GET(host, cookie, debug_mode)
    getHidden(res)
    cookie.update(res.cookies.items())
    print(cookie.items())
    try:
        res = POST(host, cookie, debug_mode, body)
        if '现在预约人数已达上限，暂时不能预约。' in res.content.decode('utf-8','ignore'):
            print(getTimeStr(),"  [Error] 预约人数已满！")
            gotify('图书馆预约结果通知', getTimeStr()+" [Error] 预约人数已满！",10).send()
            exit(1)
        getHidden(res)
        try:
            body['ctl00$MainContent$TextBox1'] = config['user']['username']
            body['ctl00$MainContent$TextBox2'] = config['user']['password']
            body['ctl00$MainContent$TextBox3'] = config['user']['phone']
            body['ctl00$MainContent$TextBox4'] = config['user']['reason']
            choice = config['user']['mode']
            chooseMode(choice)
            res = POST(host, cookie, debug_mode, body)
            con =  res.content.decode('utf-8','ignore')
            msg = re.findall(r'<span id="MainContent_XX" style="color:Red;">(.*)</span>', con,re.I)[0]
            if msg == '':
                print(getTimeStr(),"  [Success] 已预约")
                gotify('图书馆预约结果通知', getTimeStr()+msg, 10).send()
            else:
                print(getTimeStr(),"  [Success] ", msg)
                gotify('图书馆预约结果通知', getTimeStr()+msg, 10).send()
            # print(res.content.decode('utf-8','ignore'))
        except  (Timeout , ConnectionError , ReadTimeout):
            print('error')
    except  (Timeout , ConnectionError , ReadTimeout):
        print('error')
except (Timeout , ConnectionError , ReadTimeout):
    print('Error')

