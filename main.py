#coding=utf-8
'''
	2017年9月6日10:00:49
    爬取有道分享笔记
    
'''

import sys
from CrawlYDNoteShare.crawler import *


def main():
        
    dFlag	= False
    loop    = asyncio.get_event_loop()
    url     = input(" [*] 输入分享地址 ：")
    root_dir = input(" [*] 输入保存文件的目录:")
	
    print("********************************")
	
    if root_dir is "":
        crawler = Crawler(url,debug=dFlag)
    else:
        crawler = Crawler(url,root_dir=root_dir,debug=dFlag)
    
    try:
        loop.run_until_complete(crawler.crawl())
    except KeyboardInterrupt:
        sys.stderr.flush()
        print('\nInterrupted\n')
    finally:
        #关闭session
        crawler.close()
        #next two lines are required for actual aiohttp resource cleanup
        loop.stop()
        loop.run_forever()
        loop.close()



if __name__ == "__main__":
    main()