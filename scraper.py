import scraperwiki
import requests
from bs4 import BeautifulSoup
import re
import datetime
from dateutil import parser

def dropper(table,drop=False):
    """ Helper function to drop a table """
    if not drop: return
    print "dropping",table
    if table!='':
        try: scraperwiki.sqlite.execute('drop table "'+table+'"')
        except: pass

def tablesetup_str(t,drop=False):
  if drop: dropper(t,drop)
  tbdef={}
  for i in df.columns:
    if df.dtypes[i]=='float64':
      tbdef[i]='real'
    else:
      tbdef[i]='text'
  deflist=[]
  for k in tbdef:
    deflist.append("'{}' {}".format(k,tbdef[k]))
  dt="CREATE TABLE IF NOT EXISTS '{}' ({})".format(t,','.join(deflist))
  return dt

def applicationTrackingTable(p):
    data={}
    t=BeautifulSoup(p).find('div',id='pnlTracking').find('table')
    for row in t.findAll('tr'):
        cells=row.findAll('td')
        cn=re.sub('[\r\t\n]','',cells[0].text).strip().strip(':').replace(u'\xa0',' ')
        data[cn]=cells[1].text.strip()
        try:
            data[cn+'_t']=parser.parse(data[cn], dayfirst=True)
        except: 
            data[cn+'_t']=None
    return data
    
def planningAppCleaner(t):
    data={}
    for row in t.findAll('tr')[1:]:
        cells=row.findAll('td')
        key=re.sub('[\r\t\n]','',cells[0].text).strip().strip(':').replace(u'\xa0',' ')
        data[key]=re.sub('[\r\t]','',re.sub('\s\s+',' ',cells[1].text.replace(u'\xa0',' '))).strip()
    en=data['Easting/Northing'].split('/')
    data['easting']=float(en[0].strip())
    data['northing']=float(en[1].strip())
    return data

def iwPlanPageScrape(stub):
    print('Grabbing {}'.format(stub)) 
    urlbase='https://www.iwight.com/planning/'
    url=urlbase+stub
    p=requests.get(url)
    t=BeautifulSoup(p.content.replace('<br/>','\n')).find('table',id='summarydetails')
    data=planningAppCleaner(t)
    data.update(applicationTrackingTable(p.content))
    return data
    

from math import sqrt, pi, sin, cos, tan, atan2 as arctan2
#http://www.hannahfry.co.uk/blog/2012/02/01/converting-british-national-grid-to-latitude-and-longitude-ii
def OSGB36toWGS84(E,N):
    #E, N are the British national grid coordinates - eastings and northings
    a, b = 6377563.396, 6356256.909     #The Airy 180 semi-major and semi-minor axes used for OSGB36 (m)
    F0 = 0.9996012717                   #scale factor on the central meridian
    lat0 = 49*pi/180                    #Latitude of true origin (radians)
    lon0 = -2*pi/180                    #Longtitude of true origin and central meridian (radians)
    N0, E0 = -100000, 400000            #Northing & easting of true origin (m)
    e2 = 1 - (b*b)/(a*a)                #eccentricity squared
    n = (a-b)/(a+b)

    #Initialise the iterative variables
    lat,M = lat0, 0

    while N-N0-M >= 0.00001: #Accurate to 0.01mm
        lat = (N-N0-M)/(a*F0) + lat;
        M1 = (1 + n + (5./4)*n**2 + (5./4)*n**3) * (lat-lat0)
        M2 = (3*n + 3*n**2 + (21./8)*n**3) * sin(lat-lat0) * cos(lat+lat0)
        M3 = ((15./8)*n**2 + (15./8)*n**3) * sin(2*(lat-lat0)) * cos(2*(lat+lat0))
        M4 = (35./24)*n**3 * sin(3*(lat-lat0)) * cos(3*(lat+lat0))
        #meridional arc
        M = b * F0 * (M1 - M2 + M3 - M4)          

    #transverse radius of curvature
    nu = a*F0/sqrt(1-e2*sin(lat)**2)

    #meridional radius of curvature
    rho = a*F0*(1-e2)*(1-e2*sin(lat)**2)**(-1.5)
    eta2 = nu/rho-1

    secLat = 1./cos(lat)
    VII = tan(lat)/(2*rho*nu)
    VIII = tan(lat)/(24*rho*nu**3)*(5+3*tan(lat)**2+eta2-9*tan(lat)**2*eta2)
    IX = tan(lat)/(720*rho*nu**5)*(61+90*tan(lat)**2+45*tan(lat)**4)
    X = secLat/nu
    XI = secLat/(6*nu**3)*(nu/rho+2*tan(lat)**2)
    XII = secLat/(120*nu**5)*(5+28*tan(lat)**2+24*tan(lat)**4)
    XIIA = secLat/(5040*nu**7)*(61+662*tan(lat)**2+1320*tan(lat)**4+720*tan(lat)**6)
    dE = E-E0

    #These are on the wrong ellipsoid currently: Airy1830. (Denoted by _1)
    lat_1 = lat - VII*dE**2 + VIII*dE**4 - IX*dE**6
    lon_1 = lon0 + X*dE - XI*dE**3 + XII*dE**5 - XIIA*dE**7

    #Want to convert to the GRS80 ellipsoid. 
    #First convert to cartesian from spherical polar coordinates
    H = 0 #Third spherical coord. 
    x_1 = (nu/F0 + H)*cos(lat_1)*cos(lon_1)
    y_1 = (nu/F0+ H)*cos(lat_1)*sin(lon_1)
    z_1 = ((1-e2)*nu/F0 +H)*sin(lat_1)

    #Perform Helmut transform (to go between Airy 1830 (_1) and GRS80 (_2))
    s = -20.4894*10**-6 #The scale factor -1
    tx, ty, tz = 446.448, -125.157, + 542.060 #The translations along x,y,z axes respectively
    rxs,rys,rzs = 0.1502,  0.2470,  0.8421  #The rotations along x,y,z respectively, in seconds
    rx, ry, rz = rxs*pi/(180*3600.), rys*pi/(180*3600.), rzs*pi/(180*3600.) #In radians
    x_2 = tx + (1+s)*x_1 + (-rz)*y_1 + (ry)*z_1
    y_2 = ty + (rz)*x_1  + (1+s)*y_1 + (-rx)*z_1
    z_2 = tz + (-ry)*x_1 + (rx)*y_1 +  (1+s)*z_1

    #Back to spherical polar coordinates from cartesian
    #Need some of the characteristics of the new ellipsoid    
    a_2, b_2 =6378137.000, 6356752.3141 #The GSR80 semi-major and semi-minor axes used for WGS84(m)
    e2_2 = 1- (b_2*b_2)/(a_2*a_2)   #The eccentricity of the GRS80 ellipsoid
    p = sqrt(x_2**2 + y_2**2)

    #Lat is obtained by an iterative proceedure:   
    lat = arctan2(z_2,(p*(1-e2_2))) #Initial value
    latold = 2*pi
    while abs(lat - latold)>10**-16: 
        lat, latold = latold, lat
        nu_2 = a_2/sqrt(1-e2_2*sin(latold)**2)
        lat = arctan2(z_2+e2_2*nu_2*sin(latold), p)

    #Lon and height are then pretty easy
    lon = arctan2(y_2,x_2)
    H = p/cos(lat) - nu_2

#Uncomment this line if you want to print the results
    #print [(lat-lat_1)*180/pi, (lon - lon_1)*180/pi]

    #Convert to degrees
    lat = lat*180/pi
    lon = lon*180/pi

    #Job's a good'n. 
    return lat, lon

    
def getCurrApplications():
  #Get base page 
  url='https://www.iwight.com/planning/planAppSearch.aspx'
  session = requests.Session()
  headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
  session.headers.update(headers)


  response =session.get(url)
  soup=BeautifulSoup(response.content)
  viewstate = soup.find('input' , id ='__VIEWSTATE')['value']
  eventvalidation=soup.find('input' , id ='__EVENTVALIDATION')['value']
  viewstategenerator=soup.find('input' , id ='__VIEWSTATEGENERATOR')['value']
  params={'__EVENTTARGET':'lnkShowAll','__EVENTARGUMENT':'','__VIEWSTATE':viewstate,
        '__VIEWSTATEGENERATOR':viewstategenerator,
        '__EVENTVALIDATION':eventvalidation,'q':'Search the site...'}
  #Get all current applications 
  headers['Referer'] = response.request.url
  headers['Origin']= 'https://www.iow.gov.uk'
  headers['Host']= 'www.iow.gov.uk'
  r=session.post(url,headers=headers,data=params)
  soup=BeautifulSoup(r.content)
  t=soup.find('table',id='dgResults')
  data=[]
  for row in t.findAll('tr')[1:]:
    d={}
    cells= row.findAll('td')
    d['ref']=cells[0].find('a').text.strip()
    d['stub']=cells[0].find('a')['href']
    d['addr']=cells[1].text.strip()
    d['desc']=cells[2].text.strip()
    d['commentsBy']=cells[3].text.strip()
    d['commentsByDate']=d['commentsBy'].replace('Comments Due By:','').strip()
    try:
        d['commentsByDate']=parser.parse(d['commentsByDate'], dayfirst=True)
    except:
        d['commentsByDate']=None
    d['scrapetime']=datetime.datetime.utcnow()
    #d.update(iwPlanPageScrape(d['stub']))
    #d['lat'],d['lon']=OSGB36toWGS84(d['easting'],d['northing'])
    data.append(d)
  return data

t='IWPLANNING'
#tablesetup_str(t)
dt="CREATE TABLE IF NOT EXISTS 'IWPLANNING' ('commentsBy' text,'addr' text,'Parish' text,'Case Officer' text,'Easting/Northing' text,'lon' real,'Publicity Date' text,'stub' text,'Agent or Applicant' text,'Location' text,'easting' real,'lat' real,'Proposal' text,'Comments Date' text,'ref' text,'Ward' text,'northing' real)"
scraperwiki.sqlite.execute(dt)
predata=getCurrApplications()
data=[]
grabbed=[x['ref'] for x in scraperwiki.sql.select("ref from  {}".format(t))]

print('Grabbed list of {} current items'.format(len(grabbed)))
for d in predata:
    if d['ref'] not in grabbed:
        d.update(iwPlanPageScrape(d['stub']))
        d['lat'],d['lon']=OSGB36toWGS84(d['easting'],d['northing'])
        data.append(d)
print('Grabbing {} unfetched items: {}'.format(len(data),','.join([x['ref'] for x in data])))
if d != []:
    scraperwiki.sqlite.save(unique_keys=['ref'],table_name=t, data=data)
