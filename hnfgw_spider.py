# -*- coding:utf-8 -*-  
"""
--------------------------------
    @Author: Dyson
    @Contact: Weaver1990@163.com
    @file: hnfgw_spider.py
    @time: 2017/6/5 14:49
--------------------------------
"""
import datetime
import traceback

import bs4
import numpy
import pandas as pd
import requests
import selenium.webdriver
import string
import os
import time
import sys


sys.path.append(sys.prefix + "\\Lib\\MyWheels")
reload(sys)
sys.setdefaultencoding('utf8')
import set_log  # log_obj.debug(文本)  "\x1B[1;32;41m (文本)\x1B[0m"
import csv_report

log_obj = set_log.Logger('hnfgw_spider.log', set_log.logging.WARNING,
                         set_log.logging.DEBUG)
log_obj.cleanup('hnfgw_spider.log', if_cleanup=True)  # 是否需要在每次运行程序前清空Log文件

key_list = [u'项目名称', u'开发公司', u'所在区域', u'容积率', u'规划总建筑面积(平方米)',
            u'未售总套数', u'未售总面积(平方米)']

class hnfgw_spider(object):
    def __init__(self):
        self.csv_report = csv_report.csv_report()
        self.headers = {'Accept': '*/*',
                       'Accept-Language': 'en-US,en;q=0.8',
                       'Cache-Control': 'max-age=0',
                       'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
                       'Connection': 'keep-alive'
                       }

    def initialization(self):
        # 初始化浏览器
        desired_capabilities = selenium.webdriver.DesiredCapabilities.PHANTOMJS.copy()

        for key, value in self.headers.iteritems():
            desired_capabilities['phantomjs.page.customHeaders.{}'.format(key)] = value
        desired_capabilities['phantomjs.page.customHeaders.User-Agent'] ='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

        return selenium.webdriver.PhantomJS(desired_capabilities=desired_capabilities)

    def parse_catalog(self, html, page_num):
        print u'正在分析目录页-Page %s\n' %page_num
        bs_obj = bs4.BeautifulSoup(html, 'html.parser')
        e_table = bs_obj.find('table', class_='tableStyle') #一整页数据
        e_trs = e_table.find_all('tr', class_='TR_BG_list') #行数据

        for row in e_trs:
            try:
                e_tds = row.find_all('td')[1:] # 去除第一列
                # 设置标题
                title = [u'项目名称', u'开发企业', u'项目地址', u'项目类型', u'已售套数', u'未售套数', u'url']
                row_data = [e.get_text(strip=True) for e in e_tds]
                url = 'http://www.hnfgw.com/WSBA/public/project/' + e_tds[0].a['href']
                row_data.append(url)
                # 按顺序填入数据与标题
                for d1,d2,addition in self.parse_details(url):
                    row_data.extend(d2.viewvalues())
                    row_data.extend(d1.viewvalues())
                    row_data.append(addition)
                if d1 and d2:
                    title.extend(d2.viewkeys())
                    title.extend(d1.viewkeys())
                    title.append(u'其他数据')
                else:
                    raise
                yield title, row_data
            except:
                log_obj.error('parse_catalog error %s\n%s' %(datetime.datetime.now(), traceback.format_exc()))

    def parse_details(self, url):
        print u'正在分析项目详情页 %s' %url
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding

            bs_obj = bs4.BeautifulSoup(resp.text, 'html.parser')
            e_tables_A, e_tables_B = bs_obj.find('div', id='infotable_jbxx').find_all('table')[:2]

            # 处理第一部分的数据
            df = pd.read_html(str(e_tables_A), encoding='utf8')[0]
            df = df.fillna('')  # 替换缺失值
            col_count = len(df.columns)
            if col_count % 2 == 0:
                # 一列标题，下一列为数据
                # 先将数据线data frame数据转化为numpy数组，然后将数组reshape改成2列
                arr = numpy.reshape(numpy.array(df), (-1, 2))
                # 去除key中的空格和冒号
                data_dict = dict(arr)

                d1 = {}
                addition= ''
                for key in data_dict:
                    if key in key_list:
                        d1[key] = data_dict[key]
                    else:
                        addition = addition + '%s:%s;' %(key, data_dict[key])
            else:
                raise

            # 处理第二部分的数据
            e_trs = e_tables_B.find_all('tr')[1:6]
            d2 = {}
            for e_tr in e_trs:
                purpose = e_tr.find_all('td')[0].get_text(strip=True)
                e_tds = e_tr.find_all('td')[3:]
                row_data = [e_td.get_text(strip=True) for e_td in e_tds]
                title0 = ['累计已售套数', '累计已售面积', '未售套数', '未售面积']
                title = map(lambda (x,y):x+'|'+y, zip(title0, [purpose,] * len(title0)))
                d2.update(dict(zip(title,row_data)))

            yield d1, d2, addition
        except:
            log_obj.error('parse_details error %s\n%s' % (datetime.datetime.now(), traceback.format_exc()))

    def main(self):
        driver = self.initialization()
        driver.get('http://www.hnfgw.com/WSBA/public/project/ProjectList.aspx')

        # 最后一页中“下一页”按钮代码，其中有disabled这一个属性，之前没有
        # <a id="PageNavigator1_LnkBtnNext" disabled="disabled" style="color:Black;">下一页</a>
        data = []
        title = []
        while True:
            page_num = driver.find_element_by_xpath('//*[@id="PageNavigator1_LblPageIndex"]').text
            print u'\n正在爬取海宁透明售房网的项目列表的第', page_num, u'页------->\n'
            html = driver.page_source
            #print html
            for title, row_data in self.parse_catalog(html, page_num):
                data.append(row_data)

            # 最后一页中出现disable这个属性，所以在爬取完最后一页之后跳出死循环
            if driver.find_element_by_xpath('//a[@id="PageNavigator1_LnkBtnNext"]').get_attribute('disabled'):
                break
            # 完成一页的动作之后，爬取下一页
            driver.find_element_by_xpath('//a[@id="PageNavigator1_LnkBtnNext"]').click()
        # 将数据写入csv文件
        self.csv_report.output_data(data, 'hnfgw_data', title=title)
        driver.close()

if __name__ == '__main__':
    hnfgw_spider = hnfgw_spider()
    hnfgw_spider.main()