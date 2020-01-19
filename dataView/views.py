# coding=utf-8
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.core.paginator import Paginator
import json
import uuid
from RecruitDataVsible import settings
import requests  # 导入requests包
from bs4 import BeautifulSoup
import datetime
import time
import os
import pandas as pd
from pandas import Series
from pandas.tseries.offsets import *
from django.db.models import Q
from django.db.models import F
from django.db.models import Count
from .models import news_info
from .models import keyword_info
import operator
from dwebsocket.decorators import accept_websocket, require_websocket

# 发送HTTP请求时的HEAD信息，用于伪装为浏览器
headersParameters = {
    'Connection': 'Keep-Alive',
    'Accept': 'text/html, application/xhtml+xml, */*',
    'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/6.1 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko'
}


def index(request):
    return render(request, 'index.html')


# ----------------
# 数据可视化 Data Visualization
# ----------------


# request网页请求

def pageConvert(request, pageName="index_i.html"):
    return render(request, pageName, locals())


def getNewsInfos(request):
    key_word = {}
    page = request.GET.get("page", 1)
    rows = request.GET.get("rows", 10)
    key_word["title"] = request.GET.get("title", "")
    # 固定时间内
    # key_word["time"] = request.GET.get("time", "")
    # 时间区间自定义
    key_word["timeFrom"] = request.GET.get("timeFrom", "空")
    key_word["timeTo"] = request.GET.get("timeTo", "")
    key_word["source"] = request.GET.get("source", "")

    result = getNewsInfoByPageAndRows(page, rows, key_word)
    return HttpResponse(json.dumps(result), content_type="application/json")


def getNewsInfoByPageAndRows(page, rows, key_word):
    # 用pandas算时间偏移量
    # if(key_word["time"]=='一周内'):
    #     queryTime = (pd.datetime.now() - DateOffset(weeks= 1)).strftime('%Y-%m-%d %H:%M:%S')
    # elif(key_word["time"] == '一月内'):
    #     queryTime = (pd.datetime.now() - DateOffset(months= 1)).strftime('%Y-%m-%d %H:%M:%S')
    # elif (key_word["time"] == '一年内'):
    #     queryTime = (pd.datetime.now() - DateOffset(years= 1)).strftime('%Y-%m-%d %H:%M:%S')
    # else:
    #     queryTime = ''

    # 时间范围用time__gte
    # news = news_info.objects.filter(Q(title__icontains=key_word["title"]) &
    #                                     Q(time__gte=queryTime) & Q(source__icontains=key_word["source"]))
    if (key_word["timeFrom"] == '空'):
        news = news_info.objects.filter(Q(title__icontains=key_word["title"]) &
                                        Q(source__icontains=key_word["source"])).order_by('-time')
    else:
        # 时间区间查询法
        timeFrom = key_word["timeFrom"] + ' 00:00:00'
        timeTo = key_word["timeTo"] + ' 23:59:59'
        news = news_info.objects.filter(Q(title__icontains=key_word["title"]) &
                                        Q(time__gte=timeFrom) & Q(time__lte=timeTo) & Q(
            source__icontains=key_word["source"])).order_by('-time')

    paginator = Paginator(news, rows)
    query_sets = paginator.page(page)
    return {"total": paginator.count, "rows": list(query_sets.object_list.values())}


def getAvgSalaryEveryCity(request):
    re = getAvgSalaryByCatetory("城市")
    return HttpResponse(json.dumps(re), content_type="application/json")


def getJobCountsByEveryCity(request):
    re = getJobCountsByCity()
    result = {}
    jobCountOfCity = sorted(re, key=lambda records: records['value'], reverse=True)[:36]
    result["jobCountOfCity"] = jobCountOfCity

    lngAndLatOfCity = {}
    for var in jobCountOfCity:
        lngAndLatOfCity[var["name"]] = ALL_CITIES_LNG_LAT[var["name"]]
    result["lngAndLatOfCity"] = lngAndLatOfCity
    return HttpResponse(json.dumps(result), content_type="application/json")


def getAvgSalaryByCityAndJobType(request):
    category = request.GET.get("category", "岗位")

    result = {}
    avgWage = getAvgSalaryByCatetory(category)
    avgWage = sorted(avgWage.items(), key=operator.itemgetter(1), reverse=True)
    if category == "城市":  # 返回前100个
        avgWage = avgWage[:200]
    names = []
    AvgWage = []

    for wage in avgWage:
        names.append(wage[0])
        AvgWage.append(wage[1])
    result["names"] = names
    result["AvgWage"] = AvgWage
    return HttpResponse(json.dumps(result), content_type="application/json")


def getJobTypeCountByCity(request):
    city = request.GET.get("city", "北京")
    jobTypeCountsDic = sorted(getEveryJobTypeCountsByCity(city), key=lambda x: x['count'], reverse=True)[:10]
    result = {}
    names = []
    counts = []
    for var in jobTypeCountsDic:
        names.append(var["post_type"])
        counts.append(var["count"])

    result["names"] = names
    result["counts"] = counts
    return HttpResponse(json.dumps(result), content_type="application/json")


def getEducationAndExperienceOfCity(request):
    result = {}
    educationName = []
    jobExperienceName = []
    postType = request.GET.get("post_type", "Java开发")

    educationDemands = getEducationDemandByJobType(postType)
    jobExperienceDemands = getJobExperienceByJobType(postType)

    for var in educationDemands:
        educationName.append(var["name"])

    for var in jobExperienceDemands:
        jobExperienceName.append(var["name"])

    result["seriesData"] = educationDemands
    result["legendData"] = educationName

    result["seriesData2"] = jobExperienceDemands
    result["legendData2"] = jobExperienceName
    return HttpResponse(json.dumps(result), content_type="application/json")


def addKeyword(request):
    keyword = request.GET.get('kw', '')
    keyword_info.objects.get_or_create(name=keyword)
    return HttpResponse(json.dumps({'msg': 'success'}), content_type="application/json")


def getKeyword(request):
    resQuery = keyword_info.objects.values_list('name', flat=True)
    res = {'data': list(resQuery)}
    return HttpResponse(json.dumps(res, ensure_ascii=False), content_type="application/json", charset='utf-8')

def deleteKeyword(request):
    keyword = request.GET.get('kw', '')
    keyword_info.objects.filter(name=keyword).delete()
    return HttpResponse(json.dumps({'msg': 'success'}), content_type="application/json")

def Redirect(url):
    res = requests.get(url, timeout=10)
    newurl = res.url
    return newurl


def baidu_search(wd, pn, timeFrom, timeTo):
    # 日志文件路径创建
    # root_path = 'C:\\logs\\'
    root_path = os.getcwd() + '\\static\\'
    # root_path = os.getcwd() + '\\'
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    fileName = str(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')) + '.txt'
    full_path = root_path + fileName
    f = open(full_path, 'w', encoding='utf8')
    res = {'filepath': full_path, 'filename': fileName, 'data': []}
    # 假数据
    # wd = '华制智能'
    # pn = 1
    # print('wd:' + wd + 'pn:' + str(pn))
    pre_link = 'test'

    # for i in range(0, (int(pn) - 1) * 10 + 1, 10):
    for i in range(0, (int(pn) - 1) * 10 + 1, 10):
        # 拼接url,判断是否需要按时间范围搜索
        if (timeFrom == '空'):
            url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&wd=' + wd + '&tn=news&ie=utf-8&pn=' + str(i)
        else:


            timeFromStamp = int(time.mktime(time.strptime(timeFrom, "%Y-%m-%d %H:%M:%S")))
            timeToStamp = int(time.mktime(time.strptime(timeTo, "%Y-%m-%d %H:%M:%S")))
            url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&wd=' + wd + '&tn=news&ie=utf-8&pn=' + str(i) + \
                  '&gpc=stf%3D' + str(timeFromStamp) + '%2C' + str(timeToStamp) + '%7Cstftype%3D2'
        # Get方式获取网页数据
        strhtml = requests.get(url, headers=headersParameters)
        strhtml.encoding = "utf-8"
        # 解析
        soup = BeautifulSoup(strhtml.text, 'lxml')
        data = soup.select('.result')

        # 重复判断
        flag_1 = True

        for item in data:
            title = item.find('a').get_text().strip()
            link = item.find('a').get('href').strip()
            if (link == pre_link):
                break
            if (flag_1):
                pre_link = link
                flag_1 = False
            # 重定向
            # link_res = Redirect(link)
            # author切片
            list_author = item.find('p', class_='c-author').get_text().strip().replace("\n", "").split('\xa0\xa0')
            source = list_author[0]
            tmpTime1 = list_author[1].lstrip()
            list_abstract = item.find('div', class_='c-summary').get_text().strip().replace("\n", "").replace('\xa0',
                                                                                                              '').replace(
                '\t', '').split()
            # x小时前格式还是标准日期格式的判断,顺便格式化时间
            if (list_abstract[2][2] == ':') & (list_abstract[1][-1] == '日'):
                abstract = list_abstract[3]
                tmpTime2 = datetime.datetime(year=int(tmpTime1[0:4]), month=int(tmpTime1[5:7]), day=int(tmpTime1[8:10]),
                                             hour=int(tmpTime1[12:14]), minute=int(tmpTime1[15:17]), second=0)
            else:
                abstract = list_abstract[2]
                if (tmpTime1[-2] == '时'):
                    now = datetime.datetime.now()
                    timedelta = datetime.timedelta(hours=int(tmpTime1[:-3]))
                    tmpTime2 = now - timedelta
                else:
                    now = datetime.datetime.now()
                    timedelta = datetime.timedelta(minutes=int(tmpTime1[:-3]))
                    tmpTime2 = now - timedelta
            resTime = tmpTime2.strftime('%Y-%m-%d %H:%M:%S')
            # 写结果
            res_item = {}
            res_item['title'] = title
            res_item['link'] = link
            res_item['source'] = source
            res_item['time'] = resTime
            res_item['abstract'] = abstract
            res['data'].append(res_item)
            # 写数据库，不重复插入
            news_info.objects.get_or_create(title=title, link=link, source=source, time=resTime, abstract=abstract)
            # 写文件
            f.write('-------------------\n')
            f.write('标题：' + title + '\n')
            f.write('链接：' + link + '\n')
            f.write('来源：' + source + '\n')
            f.write('日期：' + resTime + '\n')
            f.write('摘要：' + abstract + '\n')
            f.write('-------------------\n')
            # csv_writer.writerow([title, link, source, time, abstract])

    print('endend')
    # 关闭文件
    f.close()
    return res
    # print(soup.prettify())


def baiduNewsSpider(request):
    kw = request.GET.get("kw", '华制智能')
    pn = request.GET.get("pn", '1')
    timeFrom = request.GET.get("timeFrom", '空')
    timeTo = request.GET.get("timeTo", '空')
    if(timeFrom != '空'):
        timeFrom += ' 00:00:00'
        timeTo += ' 23:59:59'
    # try:
    res = baidu_search(kw, pn, timeFrom, timeTo)
    res['msg'] = 'success'
    return HttpResponse(json.dumps(res), content_type="application/json")
    # except Exception:
    #     return HttpResponse(json.dumps({"msg": "false"}), content_type="application/json")
    # kw = "华制智能"
    # pn = 1
    # data = {
    #     'name': 'Vitor',
    #     'location': 'Finland',
    #     'is_active': True,
    #     'count': 28
    # }
    # return HttpResponse(json.dumps(data), content_type="application/json")

    # print(baidu_search(kw, pn))


# 关键词趋势变化
def getTrendByKeyword(request):
    kw = request.GET.get("kw", '华制智能')
    resQuery = news_info.objects.filter(Q(title__icontains=kw)).values('time').order_by('time')
    timeDict = {}

    for item in resQuery:
        if (item['time'][:10] not in timeDict):
            timeDict[item['time'][:10]] = 1
        else:
            timeDict[item['time'][:10]] += 1

    res = {'time': list(timeDict.keys()), 'total': list(timeDict.values())}
    return HttpResponse(json.dumps(res), content_type="application/json")


def companyInfo(request):
    numberid = request.GET.get("numberId", "CC526060929")
    return HttpResponse(json.dumps(getCompanyInfoByNumberId(numberid)), content_type="application/json")


# request完


# 帮助方法

def getJobsInfoByPageAndRows(page, rows, key_word):
    jobs = Job.objects.filter(
        Q(city__icontains=key_word["city"]) & Q(job_experience__icontains=key_word["job_experience"]) & Q(
            education__icontains=key_word["education"]) & Q(post_type__icontains=key_word["post_type"]))
    paginator = Paginator(jobs, rows)
    query_sets = paginator.page(page)

    return {"total": paginator.count, "rows": list(query_sets.object_list.values())}


def getAvgSalaryByCatetory(category):
    result = {}
    if category == "岗位":
        allPostTypes = getSingleFiledAndDistinct("post_type")
        for postType in allPostTypes:
            salaries = Job.objects.filter(post_type=postType).values("max_wage", "min_wage")
            sa_num = 0.0
            for salary in salaries:
                sa_num += float(salary["max_wage"]) + float(salary["min_wage"])
            sa_num /= 2.0 * len(salaries)
            result[postType] = round(sa_num, 1)

    elif category == "城市":
        allCities = getSingleFiledAndDistinct("city")
        for city in allCities:
            salaries = Job.objects.filter(city=city).values("max_wage", "min_wage")
            sa_num = 0.0
            for salary in salaries:
                sa_num += float(salary["max_wage"]) + float(salary["min_wage"])
            sa_num /= 2.0 * len(salaries)
            result[city] = round(sa_num, 1)

    return result


def getSingleFiledAndDistinct(filed):
    return list(Job.objects.values_list(filed, flat=True).distinct().order_by(filed))


def getJobCountsByCity():
    return list(
        Job.objects.values('city').annotate(name=F('city'), value=Count('name')).values('name', 'value').order_by())


# def getEducationDemandEveryJobType():
#     result = {}
#     allPostTypes = getSingleFiledAndDistinct("post_type")
#     for postType in allPostTypes:
#         result[postType] = getEducationDemandByJobType(postType)
#
#     return result


def getEducationDemandByJobType(JobType):
    return list(Job.objects.filter(post_type=JobType).values("education").annotate(name=F('education'),
                                                                                   value=Count('name')).values('name',
                                                                                                               'value').order_by())


def getJobExperienceByJobType(JobType):
    return list(Job.objects.filter(post_type=JobType).values("job_experience").annotate(name=F('job_experience'),
                                                                                        value=Count('name')).values(
        'name', 'value').order_by())


# def getEveryJobTypeCountsEveryCity():
#     result = {}
#     allCities = getSingleFiledAndDistinct("city")
#     for city in allCities:
#         result[city] = getEveryJobTypeCountsByCity(city)
#
#     return result


def getEveryJobTypeCountsByCity(city):
    return list(Job.objects.filter(city=city).values("post_type").annotate(count=Count('post_type')).values('post_type',
                                                                                                            'count').order_by(
        "count"))


def getCompanyInfoByNumberId(numberId):
    return list(Company.objects.filter(number=numberId).values())

# 帮助方法完
