import json
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus, unquote,urlencode
from datetime import datetime, date, timedelta
import requests, json
from collections import OrderedDict
import pytz
import geopy
from geopy.geocoders import Nominatim
import math
NX = 149            ## X축 격자점 수
NY = 253            ## Y축 격자점 수

Re = 6371.00877     ##  지도반경
grid = 5.0          ##  격자간격 (km)
slat1 = 30.0        ##  표준위도 1
slat2 = 60.0        ##  표준위도 2
olon = 126.0        ##  기준점 경도
olat = 38.0         ##  기준점 위도
xo = 210 / grid     ##  기준점 X좌표
yo = 675 / grid     ##  기준점 Y좌표
first = 0

if first == 0 :
    PI = math.asin(1.0) * 2.0
    DEGRAD = PI/ 180.0
    RADDEG = 180.0 / PI


    re = Re / grid
    slat1 = slat1 * DEGRAD
    slat2 = slat2 * DEGRAD
    olon = olon * DEGRAD
    olat = olat * DEGRAD

    sn = math.tan(PI * 0.25 + slat2 * 0.5) / math.tan(PI * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(PI * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(PI * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)
    first = 1

def mapToGrid(lat, lon, code = 0 ):
    ra = math.tan(PI * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > PI :
        theta -= 2.0 * PI
    if theta < -PI :
        theta += 2.0 * PI
    theta *= sn
    x = (ra * math.sin(theta)) + xo
    y = (ro - ra * math.cos(theta)) + yo
    x = int(x + 1.5)
    y = int(y + 1.5)
    return x, y

def gridToMap(x, y, code = 1):
    x = x - 1
    y = y - 1
    xn = x - xo
    yn = ro - y + yo
    ra = math.sqrt(xn * xn + yn * yn)
    if sn < 0.0 :
        ra = -ra
    alat = math.pow((re * sf / ra), (1.0 / sn))
    alat = 2.0 * math.atan(alat) - PI * 0.5
    if math.fabs(xn) <= 0.0 :
        theta = 0.0
    else :
        if math.fabs(yn) <= 0.0 :
            theta = PI * 0.5
            if xn < 0.0 :
                theta = -theta
        else :
            theta = math.atan2(xn, yn)
    alon = theta / sn + olon
    lat = alat * RADDEG
    lon = alon * RADDEG

    return lat, lon

def get_style(a):
	return {
		1: "패딩, 두꺼운 코트, 목도리, 기모제품",
		2: "코트, 가죽자켓, 히트텍, 니트, 레깅스",
		3: "자켓, 트렌치 코트, 야상, 니트, 청바지, 스타킹",
		4: "자켓, 가디건, 야상, 스타킹, 청바지, 면바지",
		5: "얇은 니트, 맨투맨, 가디건, 청바지",
		6: "얇은 가디건, 긴 팔, 면바지, 청바지",
		7: "반팔, 얇은 셔츠, 반바지, 면바지",
		8: "민소매, 반팔, 반바지, 원피스"
	}.get(a, "추천할 옷이 없습니다.")

def get_sky(a):
    return {
        1: "맑음",
        3: "구름많음",
        4: "흐림"
    }.get(a, "정보 없음")

KST = pytz.timezone('Asia/Seoul')

def weather_func(a, b):
    
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst'

    load_dotenv()
    key = os.environ.get('SERVICE_KEY')
    key_decoded = unquote(key, encoding='utf-8')
    
    now = datetime.now(KST) 
    today = datetime.today().strftime('%Y%m%d')
    y = date.today() - timedelta(days=1)
    yesterday = y.strftime('%Y%m%d')
    nx = a
    ny = b

    if now.minute < 45:
        if now.hour == 0:
            base_time = '2330'
            base_date = yesterday
        else:
            pre_hour = now.hour - 1
            if pre_hour < 10:
                base_time = f'0{str(pre_hour)}30'
            else:
                base_time = f'{str(pre_hour)}30'
            base_date = today
    else:
        if now.hour < 10:
            base_time = f'0{str(now.hour)}30'
        else:
            base_time = f'{str(now.hour)}30'
        base_date = today
    print(f'{base_date}-{base_time}')
    query_param = {'serviceKey' : key_decoded, 'base_date' : base_date, 
                'base_time' : base_time, 'numOfRows' : 60, 
                'dataType' : 'json', 'nx' : nx, 'ny': ny}
    res = requests.get(url, params=query_param)
    items = res.json()['response']['body']['items']
    file_path = f'/Users/dorong/Programming/Python/초단기강수예측카톡bot/{base_date}-{base_time}.json'
    # LGT(낙뢰), PTY(강수형태), RN1(1시간 강수량), SKY(하늘상태)
    # T1H(기온), REH(습도), UUU(풍속(동서성분), VVV(남북성분), 
    # VEC(풍향), WSD(풍속)
    
    date_list = []
    time_list = []
    for item in items['item']:
        d = item['fcstDate']
        time = item['fcstTime']
        if not time in time_list:
            time_list.append(time)
        if not d in date_list:
            date_list.append(d)
    
    weather_data = OrderedDict()
    temp = 0
    for d in date_list:
        weather_data[d] = []
        for t in time_list:
            weather_value = OrderedDict()
            weather_time = OrderedDict()
            for item in items['item']:
                if item['fcstDate'] == d:
                    if item['fcstTime'] == t:
                        time = f"{t[0:2]}시"
                        weather_time[time] = []
                        if item['category'] == 'T1H':
                            weather_value['온도'] = f"{item['fcstValue']}도"
                            temp += float(item['fcstValue'])
                        if item['category'] == 'REH':
                            weather_value['습도'] = f"{item['fcstValue']}%"
                        if item['category'] == 'SKY':
                            weather_value['하늘'] = get_sky(int(item['fcstValue']))
                        if item['category'] == 'RN1':
                            weather_value['강수량'] = item['fcstValue']
                            if not '강수없음' in weather_value['강수량']:
                                weather_value['우산'] = "우산이 필요합니다."
            if weather_value:
                weather_time[time] = weather_value
                weather_data[d].append(weather_time)
    if temp != 0:
        temp = temp/6
        weather_data['오늘의 평균온도'] = f'{round(temp, 2)}도'
    else :
        weather_data['오늘의 평균온도'] = '0도'
    
    clothes = 0
    if temp < 5:
        clothes = 1
    elif 5 <= temp < 9:
        clothes = 2
    elif 9 <= temp < 12:
        clothes = 3
    elif 12 <= temp < 17:
        clothes = 4
    elif 17 <= temp < 20:
        clothes = 5
    elif 20 <= temp < 23:
        clothes = 6
    elif 23 <= temp < 28:
        clothes = 7
    elif temp >= 28:
        clothes = 8
        
    weather_data['오늘의 옷차림'] = get_style(clothes)
    return weather_data

def geocoding(address):
    geolocoder = Nominatim(user_agent = 'South Korea', timeout=None)
    geo = geolocoder.geocode(address)
    crd = {"lat": str(geo.latitude), "lng": str(geo.longitude)}
    geopy.point.Point
    location = geolocoder.reverse(geo.latitude, geo.longitude)
    return crd, location

def lambda_handler(event, context):
    address = str(event['queryStringParameters']['address'])
    crd, location = geocoding(address)
    a, b = float(crd['lat']), float(crd['lng'])
    x, y = mapToGrid(a, b)
    w = weather_func(x, y)
    w['위도_경도'] = (a, b)
    w['입력한 주소'] = location
    return {
        'statusCode' : 200,
        'headers': {
                "content-type":"application/json; charset=utf-8"
        },
        'body' : json.dumps(w, indent=4, sort_keys=True, ensure_ascii=False)
    }