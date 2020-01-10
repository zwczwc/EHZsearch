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
import os
from pandas import Series
from django.db.models import Q
from django.db.models import F
from django.db.models import Count
from .models import news_info
import operator
from dwebsocket.decorators import accept_websocket,require_websocket

#发送HTTP请求时的HEAD信息，用于伪装为浏览器
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


#request网页请求

def pageConvert(request,pageName="index_i.html"):
    return render(request, pageName,locals())
def getNewsInfos(request):
    key_word = {}
    page = request.GET.get("page", 1)
    rows = request.GET.get("rows", 10)
    key_word["title"] = request.GET.get("title", "")
    key_word["time"] = request.GET.get("time", "")
    key_word["source"] = request.GET.get("source", "")

    result = getJobsInfoByPageAndRows(page, rows, key_word)
    return HttpResponse(json.dumps(result), content_type="application/json")

def getNewsInfoByPageAndRows(page,rows,key_word):
    news = news_info.objects.filter(Q(title__icontains=key_word["title"]) & Q(time__icontains=key_word["time"]) &Q(source__icontains=key_word["source"]))
    paginator = Paginator(news,rows)
    query_sets = paginator.page(page)
    return {"total": paginator.count, "rows": list(query_sets.object_list.values())}


def getJobInfos(request):
     key_word = {}
     page = request.GET.get("page",1)
     rows = request.GET.get("rows",10)
     key_word["city"] = request.GET.get("city","")
     key_word["job_experience"] = request.GET.get("job_experience", "")
     key_word["education"] = request.GET.get("education", "")
     key_word["post_type"] = request.GET.get("post_type", "")

     result = getJobsInfoByPageAndRows(page, rows, key_word)
     return  HttpResponse(json.dumps(result), content_type="application/json")




def getAvgSalaryEveryCity(request):
    re = getAvgSalaryByCatetory("城市")
    return HttpResponse(json.dumps(re), content_type="application/json")


def getJobCountsByEveryCity(request):
    re = getJobCountsByCity()
    result = {}
    jobCountOfCity = sorted(re,key=lambda records:records['value'], reverse = True)[:36]
    result["jobCountOfCity"] = jobCountOfCity

    lngAndLatOfCity = {}
    for var in jobCountOfCity:
        lngAndLatOfCity[var["name"]] = ALL_CITIES_LNG_LAT[var["name"]]
    result["lngAndLatOfCity"] = lngAndLatOfCity
    return HttpResponse(json.dumps(result), content_type="application/json")

def getAvgSalaryByCityAndJobType(request):
    category = request.GET.get("category","岗位")

    result = {}
    avgWage = getAvgSalaryByCatetory(category)
    avgWage = sorted(avgWage.items(), key = operator.itemgetter(1), reverse = True)
    if category=="城市":  #返回前100个
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
    city = request.GET.get("city","北京")
    jobTypeCountsDic = sorted(getEveryJobTypeCountsByCity(city),key=lambda x:x['count'], reverse=True)[:10]
    result = {}
    names=[]
    counts=[]
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
     postType = request.GET.get("post_type","Java开发")

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

def Redirect(url):
    res = requests.get(url, timeout=10)
    newurl = res.url
    return newurl

def baidu_search(wd, pn):
    #日志文件路径创建
    root_path = 'C:\\logs\\'
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    fileName = str(datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')) + '.txt'
    full_path = root_path + fileName
    f = open(full_path,'w',encoding='utf8')
    res = {'filepath': full_path, 'data': []}
    #假数据
    # wd = '华制智能'
    pn = 1
    print('wd:'+wd+'pn:'+str(pn))
    pre_link = 'test'
    cnt = 0
    # for i in range(0, (int(pn) - 1) * 10 + 1, 10):
    for i in range(0, (int(pn) - 1) * 10 + 1, 10):
        # 拼接url
        # url = 'https://www.baidu.com/baidu?wd='+wd+'&tn=monline_dg&ie=utf-8&pn='+str(i)
        url = 'https://www.baidu.com/s?rtt=1&bsst=1&cl=2&wd=' + wd + '&tn=news&ie=utf-8&pn=' + str(i)
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
            if(flag_1):
                pre_link = link
                flag_1 = False
            # 重定向
            # link_res = Redirect(link)
            # author切片
            list_author = item.find('p', class_='c-author').get_text().strip().replace("\n", "").split('\xa0\xa0')
            source = list_author[0]
            time = list_author[1].lstrip()
            list_abstract = item.find('div', class_='c-summary').get_text().strip().replace("\n", "").replace('\xa0','').replace('\t','').split()
            #x小时前格式还是标准日期格式的判断
            if(list_abstract[2][2] == ':'):
                abstract = list_abstract[3]
            else:
                abstract = list_abstract[2]

            res_item = {}

            res_item['title'] = title
            res_item['link'] = link
            res_item['source'] = source
            res_item['time'] = time
            res_item['abstract'] = abstract
            res['data'].append(res_item)
            #写数据库
            news_info.objects.create(title=title,link=link,source=source,time=time,abstract=abstract)
            #写文件
            f.write('-------------------\n')
            f.write('标题：'+ title +'\n')
            f.write('链接：' + link + '\n')
            f.write('来源：' + source + '\n')
            f.write('日期：' + time + '\n')
            f.write('摘要：' + abstract + '\n')
            f.write('-------------------\n')
            # abstract = list(summary)[1]
            # print(title,link,source,time,abstract)
            #csv_writer.writerow([title, link, source, time, abstract])

    print('endend')
    # 关闭文件
    f.close()
    return res
    # print(soup.prettify())

def baiduNewsSpider(request):
    kw = request.GET.get("kw")
    pn = request.GET.get("pn")
    # try:
    return HttpResponse(json.dumps(baidu_search(kw, pn)), content_type="application/json")
    # except Exception:
    #       return HttpResponse(json.dumps({"msg": "false"}), content_type="application/json")
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




def companyInfo(request):
    numberid = request.GET.get("numberId","CC526060929")
    return HttpResponse(json.dumps(getCompanyInfoByNumberId(numberid)), content_type="application/json")

#request完



#帮助方法

def getJobsInfoByPageAndRows(page,rows,key_word):
    jobs = Job.objects.filter(Q(city__icontains=key_word["city"]) & Q(job_experience__icontains=key_word["job_experience"]) &Q(education__icontains=key_word["education"]) &Q(post_type__icontains=key_word["post_type"]))
    paginator = Paginator(jobs,rows)
    query_sets = paginator.page(page)

    return {"total":paginator.count,"rows":list(query_sets.object_list.values())}

def getAvgSalaryByCatetory(category):
    result = {}
    if category=="岗位":
        allPostTypes = getSingleFiledAndDistinct("post_type")
        for postType in allPostTypes:
            salaries = Job.objects.filter(post_type=postType).values("max_wage","min_wage")
            sa_num = 0.0
            for salary in salaries:
                sa_num +=float(salary["max_wage"])+float(salary["min_wage"])
            sa_num /= 2.0*len(salaries)
            result[postType] = round(sa_num,1)

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
    return list(Job.objects.values_list(filed,flat=True).distinct().order_by(filed))

def getJobCountsByCity():
    return list(Job.objects.values('city').annotate(name=F('city'),value=Count('name')).values('name', 'value').order_by())

# def getEducationDemandEveryJobType():
#     result = {}
#     allPostTypes = getSingleFiledAndDistinct("post_type")
#     for postType in allPostTypes:
#         result[postType] = getEducationDemandByJobType(postType)
#
#     return result


def getEducationDemandByJobType(JobType):
    return list(Job.objects.filter(post_type=JobType).values("education").annotate(name=F('education'),value=Count('name')).values('name', 'value').order_by())

def getJobExperienceByJobType(JobType):
    return list(Job.objects.filter(post_type=JobType).values("job_experience").annotate(name=F('job_experience'),value=Count('name')).values('name', 'value').order_by())

# def getEveryJobTypeCountsEveryCity():
#     result = {}
#     allCities = getSingleFiledAndDistinct("city")
#     for city in allCities:
#         result[city] = getEveryJobTypeCountsByCity(city)
#
#     return result


def getEveryJobTypeCountsByCity(city):
    return list(Job.objects.filter(city=city).values("post_type").annotate(count=Count('post_type')).values('post_type','count').order_by("count"))


def getCompanyInfoByNumberId(numberId):
    return list(Company.objects.filter(number=numberId).values())


#帮助方法完

