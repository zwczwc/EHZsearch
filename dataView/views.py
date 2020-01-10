# coding=utf-8
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.core.paginator import Paginator
import json
import uuid
from RecruitDataVsible import settings
import time

from pandas import Series
from django.db.models import Q
from django.db.models import F
from django.db.models import Count
from .ehzsearch import baidu_search
import operator
from dwebsocket.decorators import accept_websocket,require_websocket

def index(request):
    return render(request, 'index.html')


# ----------------
# 数据可视化 Data Visualization
# ----------------


#request网页请求

def pageConvert(request,pageName="index_i.html"):
    return render(request, pageName,locals())

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

def baiduNewsSpider(request):
    kw = request.GET.get("kw")
    pn = request.GET.get("pn")
    try:
        return HttpResponse(json.dumps(baidu_search(kw, pn)), content_type="application/json")
    except Exception:
          return HttpResponse(json.dumps({"msg": "false"}), content_type="application/json")
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

