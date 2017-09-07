#coding=utf-8
'''
    2017年9月6日13:06:23
    @author: GG
'''
from asyncio import Queue
import asyncio
import aiohttp
import aiofiles

import re
import time
import json
import logging
import os



class Crawler:
    def __init__(self,root_url,root_dir="save",debug=False,*,loop=None):
        self.loop       = loop or asyncio.get_event_loop()
        self.max_tasks  = 10
        self.q          = Queue(loop=self.loop)
        self.root_dir   = root_dir
        self.q.put_nowait([self.url_replace(root_url),self.root_dir])
        
        self.t0         = time.time()
        self.t1         = None
        self.session    = aiohttp.ClientSession(loop=self.loop)#打开HTTP sesion会话
        self.headers    = {
                    "Host": "note.youdao.com",
                    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
        }
        
        self.isFirst = True
        
        #提取笔记的id和sub的正则
        self.idRE = re.compile(r'id=([0-9a-zA-Z])+')
        self.subRE = re.compile(r'sub=([0-9a-zA-Z])+')
        if self.idRE.search(root_url):
            self.shareId = self.idRE.search(root_url).group(0)[3:]
        #开启log   
        if debug:
            logging.basicConfig(level=logging.INFO)    
            
        
    def url_replace(self,url):
        #分享的目录
        notebookURL = "http://note.youdao.com/yws/public/notebook/" 
        #分享的文件内容
        noteURL = ("http://note.youdao.com/yws/api/personal/file/{}"
                   "?method=download&read=true&shareKey={}&cstk=false")
        if ('sub' in url) and ('id' in url):
            subM = self.subRE.search(url)
            idM = self.idRE.search(url)
            if subM and idM:
                sub = subM.group(0)[4:]
                id = idM.group(0)[3:]
                url = noteURL.format(sub,id)
                return url
            return None
            
        elif 'id' in url :   
            #提取连接中的id
            id = url.split('id=')[1][:32]
            url = notebookURL+id
            return url
        else:
            return None

    async def crawl(self):
        #添加max_tasks个任务
        workers = [asyncio.Task(self.work(), loop=self.loop) for _ in range(self.max_tasks)]
		
        #当所有任务都完成时退出
        #Queue().join()等待队列为空时执行其他操作
        self.t0 = time.time()
        await self.q.join()
        self.t1 = time.time()
        
        for w in workers:
            w.cancel()
        
    async def work(self):
        try:
            while True:
                urlDir = await self.q.get()
                #print(urlDir)
                await self.fetch(urlDir)
                #递减计数器
                self.q.task_done()
                
        except asyncio.CancelledError:
                pass
            
            
    async def fetch(self,urlDir):
        
        resp = None
        try:
            if  urlDir[0] != None:
                resp = await self.session.get(urlDir[0],headers=self.headers,timeout=60) 
                await self.handle_resp(resp,urlDir)
            else:
                logging.info('url replace error.....')
        except :
            logging.info('fetch error ....')
        finally:
            if resp:
                resp.release()
                
    async def handle_resp(self,resp,urlDir):
        if urlDir[1].endswith(('.jpg','.png','.gif','.jpeg')):
            with open(urlDir[1], 'wb') as fd:
                while True:
                    chunk = await resp.content.read(4096)
                    if not chunk:
                        break
                    fd.write(chunk)
            print(" [*] %s has saved !" %urlDir[1] )
        else:
            respText = await resp.text()
            logging.info("handle_resp respText:\n %s " %respText)
            try:
                contentList = json.loads(respText)
                for item in contentList[2]:
                    subdirTemp      = "http://note.youdao.com/yws/public/notebook/{}/subdir/{}"
                    contentUrlTmep  = ("http://note.youdao.com/yws/api/personal/file/{}"
                                       "?method=download&read=true&shareKey={}&cstk=false")
                    imgUrlTmep      = "http://note.youdao.com/yws/api/personal/file/{}?method=download&shareKey={}&cstk=false"
                    
                    #将新的条目添加进队列
                    #如果是目录
                    if item.get('dr'):
                        
                        url = subdirTemp.format(self.shareId,item.get('p')[-32:])
                        logging.info('handle_resp dir json url handled: %s '%url)
                        self.q.put_nowait((url,os.path.join(urlDir[1],item.get('tl'))))
                    #如果是图片
                    elif item.get('tl').endswith(('.jpg','.png','.gif','.jpeg')):
                        url = imgUrlTmep.format(item.get('p')[-32:],self.shareId)
                        logging.info('handle_resp img json url handled: %s '%url)
                        self.q.put_nowait((url,os.path.join(urlDir[1],item.get('tl'))))
                    #如果是文件 
                    else:
                        url = contentUrlTmep.format(item.get('p')[-32:],self.shareId)
                        logging.info('handle_resp file json url handled: %s '%url)
                        self.q.put_nowait((url,os.path.join(urlDir[1],item.get('tl'))))
            except:
                #保存数据指定目录
                logging.info("handle_resp save file %s...",urlDir[1])
                if not os.path.exists(os.path.split(urlDir[1])[0]):
                    os.makedirs(os.path.split(urlDir[1])[0])
                await self.aioSave(urlDir[1],respText)
                print(" [*] %s has saved !" %urlDir[1])
            #如果是文件夹，返回的是json  [文件夹里面的文件（夹）数量，当前文件夹名称，里面的文件（夹）属性集合，文件夹标识]
            #print(contentList[1]) 
            #获取下级文件或目录的id
            #print(contentList[2][0].get('p')[-32:])       
        
    async def aioSave(self,path,content):
        f = await aiofiles.open(path,'w+')
        try:
            await f.write(content)
        finally:
            await f.close()
        
    #在外面被外部调用的            
    def close(self):
        self.session.close()
        










