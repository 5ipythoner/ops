#!/usr/bin/python
#coding: utf-8
#140@tins20.org
#description: Auto upload backup file to ftp
'''
脚本说明:
1. 总共为创建FTP连接,压缩项目目录,上传项目目录,回调平台
2. 日志分为控制台日志,日志文件
3. 简单修改即可加入项目
'''
#used for python2.7
#2017-08-19

from ftplib import FTP
import time
import os
import tarfile
import sys
import urllib
import base64
import logging
import logging.handlers

import socket

#日志写入文件
LOG_FILE='backup.log'
handler=logging.handlers.RotatingFileHandler(LOG_FILE,maxBytes=1024*1024,backupCount=5)
fmt='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
formater = logging.Formatter(fmt)
handler.setFormatter(formater)
logger=logging.getLogger('Backup')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

#写入控制台
console=logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formater)
logging.getLogger('Backup').addHandler(console)

day=time.strftime("%Y%m%d")
timestamp=time.strftime("%Y%m%d%H%M%S")
basedir="/opt/backup"
dest="/home/upload/%s/" %(day)
backdir="/opt/backup/%s" %day
host="ftpserver"
username="ftpuser"
password="ftppassword"
#host="127.0.0.1"
#username="tom"
#password="newday"

website="http://172.28.3.11/monkey/api/backup"

def call(projectName,backupFilePath,remoteFilePath):
    '''report backup status'''
    hostname = socket.getfqdn(socket.gethostname())
    addr = socket.gethostbyname(hostname)
    key=base64.b64encode(bytes("71cf4f2bfe9284d96654861c1b33576a"))
    backup=base64.b64encode(bytes(backupFilePath))
    host=base64.b64encode(bytes(addr))

    remote=base64.b64encode(bytes("ftp://%s/%s/%s" %(addr,day,remoteFilePath)))
    project = base64.b64encode(bytes(projectName))

    logger.debug("备份文件:%s,远程路径:%s,项目名称:%s" %(backupFilePath,"ftp://%s/%s/%s" %(addr,day,remoteFilePath),projectName))

    dic={'h':host,'k':key,'l':backup,'r':remote,'p':project}
    data = bytes(urllib.urlencode(dic))

    try:

        response = urllib.urlopen(website, data=data)
        logger.debug("远程调用:%s,发送的数据:%s" %(website,data) )
        if response.getcode() == 200:
            logger.info(u"备份回调成功,返回结果: %s" % (response.read().decode("utf-8")))
        else:
            logger.error(response.info())

    except Exception as error:
        logger.info("备份回调失败: %s" %(error))

def tar(projectName,projectPath):
    '''compress local project directry
        projectName
        projectPath
        :return backfilename
    '''

    backupFileName = "/opt/backup/%s/%s-%s.tar.gz" % (day, projectName, timestamp)

    if not os.path.exists(projectPath):
        logger.info(u"项目目录%s不存在,跳过备份任务。" % (projectPath))
        sys.exit(0)

    try:

        if not os.path.isdir(backdir):os.makedirs(backdir)
        logger.info(u"创建本地文件备份:%s" % (backupFileName))
        tar=tarfile.open(backupFileName,"w:gz")

        for root,dir,files in os.walk(projectPath):
            for x in files:
                fullpath=os.path.join(root,x)
                logger.debug("[A] %s" %(fullpath))
                tar.add(fullpath)

        tar.close()
        logger.info(u"本地文件备份创建成功:%s" %(backupFileName))
        return backupFileName

    except Exception as error:
        logger.error(u"本地文件备份创建失败！原因:%s" %error)
        return ""


def connect(host,username,password):
    'create connect '
    ftp=FTP()
    try:
        ftp.connect(host,21)
        ftp.login(username,password)
        logger.debug("当前访问的目录:%s" %(ftp.pwd()))
        logger.debug("服务器信息:%s" % (ftp.getwelcome()))
        return ftp

    except Exception as error:
        logger.error(u"ftp登录失败!原因:%s" %error)
        sys.exit(1)

def upload(ftp,src,dest):
    'upload file'
    bufsize=1024

    right=dest.rfind("/")
    path=dest[0:int(right)]

    try:
        #切换到目标目录
        str=ftp.nlst()

        logger.debug("ftp服务器目录:%s" %(str))

        if day not in str:
            ftp.mkd(day)
            logger.info(u"发现目录%s不存在,自动创建成功" %(path))

        fp = open(src, 'rb')
        ftp.storbinary('STOR %s' %(dest),fp,bufsize)
        ftp.quit()
        fp.close()

        logger.info(u"上传成功!远程访问路径:ftp://%s/%s/%s" %(host,day,dest.split("/").pop()))

        return dest.split("/").pop()

    except Exception as error:
        logger.error(u"上传失败!返回错误:%s" % (error))
        sys.exit(1)

if __name__=="__main__":

    if len(sys.argv) <3:
        print(u"缺少参数: %s  %s  %s" %(sys.argv[0],"projectName","projectPath"))
        sys.exit(1)

    projectName=sys.argv[1]
    projectPath=sys.argv[2]

    fileName=tar(projectName,projectPath)
    if len(fileName) == 0:
        logger.info(u"本地文件备份失败")
        sys.exit(1)

    dest += fileName.split("/").pop()
    ftp = connect(host,username,password)
    result=upload(ftp,fileName,dest)
    call(projectName, fileName, result)
