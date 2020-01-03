import requests  # 导入requests包
from bs4 import BeautifulSoup
import csv

headersParameters = {  # 发送HTTP请求时的HEAD信息，用于伪装为浏览器
    'Connection': 'Keep-Alive',
    'Accept': 'text/html, application/xhtml+xml, */*',
    'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/6.1 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko'
}


def Redirect(url):
    res = requests.get(url, timeout=10)
    newurl = res.url
    return newurl


def baidu_search(wd, pn):
    # 创建文件对象
    #f = open('搜索结果.csv', 'w', encoding='utf-8-sig')

    # 基于文件对象构建 csv写入对象
    #csv_writer = csv.writer(f)

    # 构建列表头
    #csv_writer.writerow(["标题", "链接", "来源", "时间", "摘要"])
    res = []
    pn = 1
    print('wd:'+wd+'pn:'+str(pn))
    for i in range(0, (pn - 1) * 10 + 1, 10):
        # 拼接url
        # url = 'https://www.baidu.com/baidu?wd='+wd+'&tn=monline_dg&ie=utf-8&pn='+str(i)
        url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&wd=' + wd + '&tn=news&ie=utf-8&pn=' + str(i)
        # Get方式获取网页数据
        strhtml = requests.get(url, headers=headersParameters)
        strhtml.encoding = "utf-8"

        # 解析
        soup = BeautifulSoup(strhtml.text, 'lxml')
        data = soup.select('.result')

        for item in data:
            title = item.find('a').get_text().strip()
            link = item.find('a').get('href').strip()
            # 重定向
            # link_res = Redirect(link)
            author = item.find('p', class_='c-author').get_text().replace("\n", "").replace(" ", "")
            # print(author)
            source = author[:-22]
            time = author[-20:]
            abstract = item.find('div', class_='c-summary').get_text().strip().replace("\n", "").split()[3]
            res_item = {}
            res_item['title'] = title
            res_item['link'] = link
            res_item['source'] = source
            res_item['time'] = time
            res_item['abstract'] = abstract
            res.append(res_item)
            # abstract = list(summary)[1]
            # print(title,link,source,time,abstract)
            #csv_writer.writerow([title, link, source, time, abstract])

    print('endend')
    return res
    # 关闭文件
    #f.close()
    # print(soup.prettify())


if __name__ == '__main__':
    # 关键字
    wd = "华制智能"
    # 需要多少页的结果
    pn = 1
    baidu_search(wd, pn)