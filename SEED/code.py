import pwmio
import time
import busio
import board
import analogio
import math
from ulab import numpy as np
import array
from audiocore import WaveFile
import displayio
import adafruit_displayio_ssd1306
import terminalio
from adafruit_display_text import label
import gc
from adafruit_st7789 import ST7789
import digitalio
from adafruit_bitmap_font import bitmap_font

from dadcbase import open_cfg

cfg_data=open_cfg()
tft_rotation=90*int(cfg_data['LCD_ROTATE'])
if (tft_rotation>270):
    tft_rotation=0
#阈值,
threshold=[0.1,0.2,0.3,0.9,1.8]
threshold[0]=(int(cfg_data['VA']))/1000.0
threshold[1]=(int(cfg_data['VB']))/1000.0
threshold[2]=(int(cfg_data['VC']))/1000.0
threshold[3]=(int(cfg_data['VD']))/1000.0
threshold[4]=(int(cfg_data['VE']))/1000.0
print(threshold)
threshold.sort()
real_threshold=[]
for xe in range(len(threshold)):
    if((threshold[xe]>=0.010)&(threshold[xe]<=3.010)):
        real_threshold.append(threshold[xe])
if(len(real_threshold)<2):
    defthreshold=[0.25,0.95]
    real_threshold=defthreshold
print(real_threshold)



##################################################
#蜂鸣器相关的变量,
##################################################
#下面这几个是音调谱频率,代表duo rei min fa suo 对应的频率
#从config.txt中读出的频率
BEEP_GND= int(cfg_data['BEEP_GND'])
BEE_A= int(cfg_data['BEEP_A'])
BEE_B= int(cfg_data['BEEP_B'])
BEE_C= int(cfg_data['BEEP_C'])
BEE_D= int(cfg_data['BEEP_D'])
BEE_E= int(cfg_data['BEEP_E'])
BEE_F= int(cfg_data['BEEP_F'])
#下面是蜂鸣持续时间,就是测出值后,响多久,
#不建议超过20ms.否则可能会干扰下一次测量值,
BEEP_MS= 5

#鸣叫的启动时间,停止时间,基于系统计ns计时器
#主循环会调函数检查这个值,然后是否继续鸣叫.
beep_time=[0,0]
#初始化变量
beep_time[0]=time.monotonic_ns()
beep_time[1]=beep_time[0]
boo_speaked = False
#蜂鸣频率 临时变量
beep_fre=BEEP_GND

#启动音频列表,调试用.
bibu=list()
bibu.append(1046)
bibu.append(1175)
bibu.append(1318)
debug_str=" "

#产生蜂鸣PWM
pwm = pwmio.PWMOut(board.D6, duty_cycle=2 ** 15, frequency=BEEP_GND, variable_frequency=True)


#测试开机启动音
'''
for i in range(len(bibu)):
    pwm.duty_cycle = 2 ** 15
    pwm.frequency = bibu[i]
    time.sleep(0.15)
    pwm.duty_cycle = 0 #stop
    time.sleep(0.05)
'''
pwm.frequency = BEEP_GND
pwm.duty_cycle = 2 ** 15
time.sleep(0.1)
pwm.duty_cycle = 0 #stop the beep
time.sleep(0.001)


#处理继续蜂鸣的函数,轮询判定是否应该继续鸣叫.
def voice_check():
    global beep_time
    global pwm
    temp =time.monotonic_ns()
    if temp>beep_time[1]:
        pwm.duty_cycle = 0 #stop
        return
    else:
        pwm.duty_cycle=2 ** 15
        return


##################################################
#ADC部分
##################################################

#list_adc是多次ADC得出结果组成列表,
#到时对他们进行排序 进行ADC滤波
list_adc=list()


#设定 ADC引脚,
#knob是输入脚,
#ad_gnd是测浮地.
#ad_bat 可以测 电池电压的二分之一.
knob = analogio.AnalogIn(board.A1)
#ad_gnd = analogio.AnalogIn(board.A0)
ad_bat =analogio.AnalogIn(board.A2)


#ADC值转换十进制函数
def get_voltage(raw):
    return (raw * 3.3) / 65536



#测量 表笔悬空的时候的阈值电压.
#有些表笔输出2.5 有些输出 7.2 有些输出3.3.
# 用于检测放开表笔. 注意阈值是 表笔输出最高电压打个折,比如95折
float_jiaozhun=2.3
tmp_f=0
for x in range(16):
    list_vcc=[]
    for m in range(10):
        list_vcc.append(knob.value)
    list_vcc.sort()
    tmp_f=list_vcc[5]+tmp_f
tmp_f=tmp_f/4
float_jiaozhun=(3.3*tmp_f)/(65536*2*2)
xuankong_v=str('%.2f' % float_jiaozhun)
print(float_jiaozhun)
#稍微降低阈值,比如测出悬空电压的3v 阈值=3*0.9=2.7v
float_jiaozhun=float_jiaozhun*0.9
#判断是否接入万用表二极管档未
fuluke_input=False
if(float_jiaozhun>=1.80):
    fuluke_input=True



#测量电池电压.没电池的版本用不上.
vbat_ad=0
list_adc.clear()
for x in range(11):
    raw = ad_bat.value
    list_adc.append(get_voltage(raw))
list_adc.sort() #排序,
#直接取中值
vbat_ad=list_adc[5]
vbat_ad=vbat_ad*2

#测量红表笔打到地的电压,
#红笔即使接地,ADC内部还是会浮动测出1-50MV的电压的,把它滤掉,
#如果想省出来一个IO口可以直接判定35MV以下的值等于短路就行了.
'''
gnd_jiaozhun=0.050
tmp_f=0
for x in range(16):
    list_gnd=[]
    for m in range(10):
        list_gnd.append(ad_gnd.value)
    list_gnd.sort()
    tmp_f=list_gnd[5]+tmp_f
tmp_f=tmp_f/4
gnd_jiaozhun=(3.3*tmp_f)/(65536*2*2)
print(gnd_jiaozhun)
'''
gnd_jiaozhun=(int(cfg_data['VGND']))/1000.0
#稍微增加GND 阈值. 比如测出短接表笔时候是20 mv
#那最好是把低于20*1.2以下都判断为短路
gnd_jiaozhun=gnd_jiaozhun*1.2


######################################
#下面是液晶屏显示函数
######################################
displayio.release_displays()

#复位液晶屏,
lcd_res_io=digitalio.DigitalInOut(board.D3)
lcd_res_io.direction=digitalio.Direction.OUTPUT
lcd_res_io.value = False
time.sleep(0.01)
lcd_res_io.value = True



#为LCD 增加SPI bus 通讯 接口
spi = busio.SPI(clock=board.D8, MOSI=board.D10, MISO=board.D9)
tft_cs = board.D5
tft_dc = board.D4
tft_res = board.D3

#建立显示接口
display_lcd_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display_lcd = ST7789(display_lcd_bus, width=240, height=240, rowstart=80, rotation=tft_rotation)

# Make the display context
xsplash = displayio.Group()
display_lcd.show(xsplash)
#显示logo.bmp
my_bitmap = displayio.OnDiskBitmap(open("/logo.bmp", "rb"))
my_tilegrid = displayio.TileGrid(my_bitmap, pixel_shader=displayio.ColorConverter())

xsplash.append(my_tilegrid)
time.sleep(0.5)

base_font = bitmap_font.load_font("/OP28cn.pcf")
mini_font_en = bitmap_font.load_font("/OP24.pcf")
mid_font_en = bitmap_font.load_font("/OP64.pcf")
big_font_en = bitmap_font.load_font("/OP90.pcf")
time.sleep(0.5)

#检测是否有二极管档出入(表笔浮空电压高于1.8)
errgrop = displayio.Group()
if(fuluke_input==False):
    error_display_a = label.Label(base_font,text="检测不到", color=0xFF0000, x=50, y=80)
    error_display_b = label.Label(base_font,text="二极管档输入", color=0xFF0000, x=20, y=160)
    errgrop.append(error_display_a)
    errgrop.append(error_display_b)
    display_lcd.show(errgrop)
    time.sleep(99)

#启动参数显示
cfggrop = displayio.Group()
base_y_address=14
font_hight=28
line_one=label.Label(base_font,text="悬空电压: "+xuankong_v, color=0xFF0000, x=30, y=base_y_address)
line_two=label.Label(base_font,text="电压区间", color=0xFFFFFF, x=56, y=base_y_address+font_hight*1)

line_three=label.Label(base_font,text=str(('%.3f' % gnd_jiaozhun))+"~"+str(('%.3f' % real_threshold[0])), color=0x00FF00, x=30, y=base_y_address+font_hight*2)
line_four=label.Label(base_font,text=str(('%.3f' % real_threshold[0]))+"~"+str(('%.3f' % real_threshold[1])), color=0x0000FF, x=30, y=base_y_address+font_hight*3)

str_qujianC= str(('%.3f' % real_threshold[2])) if(len(real_threshold)>2) else str('%.3f' % float_jiaozhun)
line_five=label.Label(base_font,text=str(('%.3f' % real_threshold[1]))+"~"+str_qujianC, color=0xFFFF00, x=30, y=base_y_address+font_hight*4)

str_qujianD= str(('%.3f' % real_threshold[3])) if(len(real_threshold)>3) else str('%.3f' % float_jiaozhun)
line_six=label.Label(base_font,text=str_qujianC+"~"+str_qujianD, color=0x00FFFF, x=30, y=base_y_address+font_hight*5)

str_qujianE= str(('%.3f' % real_threshold[4])) if(len(real_threshold)>4) else str('%.3f' % float_jiaozhun)
line_seven=label.Label(base_font,text=str_qujianD+"~"+str_qujianE, color=0xFF00FF, x=30, y=base_y_address+font_hight*6)

line_eight=label.Label(base_font,text=str_qujianE+"~"+str('%.3f' % float_jiaozhun), color=0x800000, x=30, y=base_y_address+font_hight*7)

cfggrop.append(line_one)
cfggrop.append(line_two)
cfggrop.append(line_three)
cfggrop.append(line_four)
cfggrop.append(line_five)
#前5行必定显示的,后3行不一定,如果只输入2个门槛电压就不用显示下面的3行了
if (len(real_threshold)>2):
    cfggrop.append(line_six)
if (len(real_threshold)>3):
    cfggrop.append(line_seven)
if (len(real_threshold)>4):
    cfggrop.append(line_eight)

display_lcd.show(cfggrop)
time.sleep(6)
#初始化新旧ADC值.
adc_new=0.1
adc_ex=adc_new
#
#初始化显示值
output_v=0.1
output_v_ex=0

#下面2个变量判断是否已经鸣叫,
#是否需要修改显示值.
#目的是避免误报,避免乱刷值.
boo_speaked=True
need_flash_lcd=True

#adc次数计算,主要用于稳定显示.和判断值是否有效.
#count_N是真实值判断次数,稳定ADC某个值大于count_N次,
#则判断有效
count_adc=0
count_N=3

#记录当前时间戳
systita_now=time.monotonic_ns()
systita_ex=systita_now

#主循环
#先布局界面
str_chh='D ADC二极管伴侣'
str_chh_display=label.Label(base_font,text=str_chh, color=0xFFFF00, x=2, y=14)
#大字体电压值,个位和小数位
ge_big_display = label.Label(mid_font_en,text='1.', color=0x6600CC, x=0, y=120)
xiaoshu_big_display = label.Label(big_font_en,text='234', color=0xFFFFFF, x=55, y=105)
#全ADC值,小字体
adc_samll_display = label.Label(mini_font_en,text='1.23456', color=0xCC0000, x=120, y=200)
#电池电压
display_bat_v= label.Label(base_font,text='bat:4.2', color=0x00FF00, x=5, y=200)

v_lcd = displayio.Group()
v_lcd.append(str_chh_display)
v_lcd.append(adc_samll_display)
v_lcd.append(display_bat_v)
v_lcd.append(ge_big_display)
v_lcd.append(xiaoshu_big_display)
display_lcd.show(v_lcd)
gc.collect()
while True:
    adc_new=0.1
    adc_ex=0.2
    count_adc=0
    #开始ADC初值.初始值不需要太准,
    tmp_f=0
    for x in range(16):
        list_dadc=[]
        for m in range(10):
            list_dadc.append(knob.value)
        list_dadc.sort()
        tmp_f=list_dadc[5]+tmp_f

    tmp_f=tmp_f/4
    adc_ex=(3.3*tmp_f)/(65536*2*2)
    #如果测出接地或者浮空就跳过下面的while循环.直接赋值.
    if(adc_ex<=gnd_jiaozhun)|(adc_ex>=float_jiaozhun):
        count_adc=count_N+1
        adc_new=adc_ex

    #内循环,跳出就表示ADC出有效值.
    #也就是要多轮ADC出一个不怎么跳变的值才是有效的.

    while(count_adc<count_N):
        #time.sleep(0.005)
        #再次ADC,判断新旧ADC值差,
        #稳定少于某个幅值才是有效值.
        tmp_f=0
        for x in range(16):
            list_dadc=[]
            for m in range(10):
                list_dadc.append(knob.value)
            list_dadc.sort()
            tmp_f=list_dadc[5]+tmp_f
            #如果表笔浮空了,跳出循环.
            over_value=0.1
            if(((list_dadc[5]*3.3)/65535)>=float_jiaozhun):
                over_value=((list_dadc[5]*3.3)/65535)
                break
        tmp_f=tmp_f/4
        adc_new=(3.3*tmp_f)/(65536*2*2)
        if(over_value>=1):
            adc_new=over_value
        #print(adc_new)

        #如果表笔浮空了,直接跳出循环.进行下次测量.
        if(adc_new>=float_jiaozhun):
            break

        tempxyz=0
        tempxyz=(adc_new-adc_ex)if (adc_new>=adc_ex) else (adc_ex-adc_new)
        #如果前后ADC值大于误差,则重新抓取count_N轮数据,
        wucha=0.020
        count_adc= 0 if (tempxyz>wucha) else (count_adc+1)
        adc_ex=adc_new
        #结束ADC循环.

    output_v=adc_new
    #判断新ADC值与液晶屏上的值是否有区别,没区别就不刷新了
    tempxyz=(output_v-output_v_ex)if (output_v>=output_v_ex) else  (output_v_ex-output_v)
    if(tempxyz>0.01):
        need_flash_lcd=True
        output_v_ex=output_v
    else:
        need_flash_lcd=False

    #判断表笔是否悬空,
    if(output_v>float_jiaozhun):
        beep_time[0]=time.monotonic_ns()
        beep_time[1]=beep_time[0]
        boo_speaked=True
        pwm.frequency = BEEP_GND
        pwm.duty_cycle = 0 #stop the beep
        ge_big_display.text='  '
        xiaoshu_big_display.text='OL'
        adc_samll_display.text=str(output_v)
        need_flash_lcd=False

    #下面是接地音效
    if(output_v<=gnd_jiaozhun):
        adc_samll_display.text=str(output_v)
        output_v=0
        pwm.frequency = BEEP_GND
        beep_time[0]=time.monotonic_ns()
        beep_time[1]=beep_time[0]+(5*BEEP_MS*1000000)
        boo_speaked=False
        debug_str="gndd"
    #下面是蜂鸣器发声配置.
    if(gnd_jiaozhun<output_v):
        if(boo_speaked==True):
            if((gnd_jiaozhun<output_v)&(output_v<=float_jiaozhun)):
                beep_time[0]=time.monotonic_ns()
                beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                boo_speaked=False
                pwm.duty_cycle=2 ** 15
                if(gnd_jiaozhun<output_v):
                    pwm.frequency = BEE_A
                if(real_threshold[0]<output_v):
                    pwm.frequency = BEE_B
                if(real_threshold[1]<output_v):
                    pwm.frequency = BEE_C
                if (len(real_threshold)>2):
                    if(real_threshold[2]<=output_v):
                        pwm.frequency = BEE_D
                if (len(real_threshold)>3):
                    if(real_threshold[3]<=output_v):
                        pwm.frequency = BEE_E
                if (len(real_threshold)>4):
                    if(real_threshold[4]<=output_v):
                        pwm.frequency = BEE_F

    #检测蜂鸣启停函数.死循环内会不停轮询.
    voice_check()


    #刷屏函数,不用整天刷液晶屏,乱跳没意义.
    if(need_flash_lcd==True):
        need_flash_lcd=False
        print('+++++++++')
        print(output_v)

        #处理数值,ADC电压的个位,小数位分别显示.
        ge=int(output_v)
        xiaoshu=output_v-ge
        #big_number
        str_ge=str(ge)+'.'
        xiaoshu=('%.3f' % xiaoshu)
        xiaoshu=str(xiaoshu)
        xiaoshu=xiaoshu[2:5]
        ge_big_display.text=str_ge
        xiaoshu_big_display.text=xiaoshu


        #output_v=('%.4f' % output_v)
        v_display= str(output_v)
        adc_samll_display.text=v_display

        bat_str=vbat_ad
        v_display= str(bat_str)
        v_display='电池:'+v_display[0:3]
        display_bat_v.text=v_display

