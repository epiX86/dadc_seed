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

BEE_A= 2750
BEE_B= 1046
BEE_C= 1175
BEE_D= 1318
BEE_E= 1397
BEE_F= 1568
BEEP_MS= 10

bibu=list()
bibu.append(BEE_A)
bibu.append(BEE_B)
bibu.append(BEE_C)
bibu.append(BEE_D)
bibu.append(BEE_E)
bibu.append(BEE_F)
debug_str=" "

######################################


######################################
displayio.release_displays()

#复位RES引脚
lcd_res_io=digitalio.DigitalInOut(board.D3)
lcd_res_io.direction=digitalio.Direction.OUTPUT
lcd_res_io.value = False
time.sleep(0.1)
lcd_res_io.value = True



#为LCD 增加SPI bus接口
spi = busio.SPI(clock=board.D8, MOSI=board.D10, MISO=board.D9)
tft_cs = board.D5
tft_dc = board.D4
#tft_bl = board.GP15
tft_res = board.D3

display_lcd_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display_lcd = ST7789(display_lcd_bus, width=240, height=240, rowstart=80, rotation=0)

# Make the display context
xsplash = displayio.Group()
display_lcd.show(xsplash)

color_bitmap = displayio.Bitmap(240, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x00FF00  # Bright Green
#生成一个绿色底板
bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
xsplash.append(bg_sprite)

my_bitmap = displayio.OnDiskBitmap(open("/logo.bmp", "rb"))
my_tilegrid = displayio.TileGrid(my_bitmap, pixel_shader=displayio.ColorConverter())
xsplash.append(my_tilegrid)
time.sleep(2)




#while True:
    #time.sleep(1999)

#time.sleep(1999)



#设定 ADC引脚, knob是输入脚, ad_gnd是测浮地.
knob = analogio.AnalogIn(board.A1)
ad_gnd = analogio.AnalogIn(board.A0)
ad_bat =analogio.AnalogIn(board.A2)

#二进制ADC值 转换十进制电压,
def get_voltage(raw):
    return (raw * 3.3) / 65536



#蜂鸣器相关的变量,
beep_time=[0,0] #启动时间,停止时间,基于系统计ns计时器
beep_time[0]=time.monotonic_ns()
beep_time[1]=beep_time[0]
boo_speaked = False
#蜂鸣频率 临时变量
beep_fre=4500

#产生蜂鸣PWM
pwm = pwmio.PWMOut(board.D6, duty_cycle=2 ** 15, frequency=7500, variable_frequency=True)

#测试开机启动音
'''
for i in range(len(bibu)):
    pwm.duty_cycle = 2 ** 15
    pwm.frequency = bibu[i]
    time.sleep(0.1)
    pwm.duty_cycle = 0 #stop
    time.sleep(0.05)
    pwm.duty_cycle = 2 ** 15 #start
    time.sleep(0.1)
    pwm.duty_cycle = 0 #stop
    time.sleep(0.05)
#time.sleep(0.1)
#pwm.frequency = BEE_A
#time.sleep(0.1)
'''
pwm.duty_cycle = 0 #stop
time.sleep(0.1)

#time.sleep(0.05)


#检测是继续蜂鸣的函数,轮询的.
def voice_check():
    global beep_time
    global pwm
    temp =time.monotonic_ns()
    if temp>beep_time[1]:
        pwm.duty_cycle = 0 #stop
        return
    else:
        pwm.duty_cycle=2 ** 15
        #pwm.frequency = beep_fre
        return

list_adc=list()
#表笔悬空的时候的阈值电压.
#有些表笔输出2.5 有些输出 7.2 有些输出3.3.
#机身ADC限制最高是3.3
float_jiaozhun=3.300*0.95
list_adc.clear()
for x in range(100):
    raw = knob.value
    list_adc.append(get_voltage(raw))
list_adc.sort() #排序,
#直接取中值
float_jiaozhun=list_adc[50]
#稍微降低阈值,比如测出悬空电压的3v 阈值=3*0.9=2.7v
float_jiaozhun=float_jiaozhun*0.9

#获取电池电压.
vbat_ad=0
list_adc.clear()
for x in range(11):
    raw = ad_bat.value
    list_adc.append(get_voltage(raw))
list_adc.sort() #排序,
#直接取中值
vbat_ad=list_adc[5]
vbat_ad=vbat_ad*2



jiaozhun=0.999
#先ADC一次对地电压,避免检测到0.03以下这种值,直接等于0
#gnd_jiaozhun对地电压,少于这个值等于0
gnd_jiaozhun=0.001
list_adc.clear()
for x in range(500):
    raw = ad_gnd.value
    list_adc.append(get_voltage(raw))
list_adc.sort() #排序,然后删除最高最低各50个数据
for i in range(50):
    list_adc.pop(0)
    list_adc.pop(-1)
gnd_jiaozhun=np.mean(list_adc)
#稍微增加GND 阈值.
gnd_jiaozhun=gnd_jiaozhun*1.2




boo_speaked=True
adc_new=0.1
adc_ex=adc_new
systita_now=time.monotonic_ns()
systita_ex=systita_now
output_v=0.1

count_adc=0
count_N=30
output_v_ex=0
need_flash_lcd=True
while True:


    adc_new=0
    adc_ex=0
    count_adc=0
    #采样110次,丢弃
    o_v_list=list()

    list_adc.clear()
    for i in range(11):
        raw = knob.value
        list_adc.append(get_voltage(raw))
    list_adc.sort()
    adc_new=(list_adc[5])
    count_adc=0

    while(count_adc<count_N):
        time.sleep(0.001)
        tempxyz=0
        adc_ex=adc_new
        list_adc.clear()
        for i in range(11):
            raw = knob.value
            list_adc.append(get_voltage(raw))
        list_adc.sort()
        adc_new=(list_adc[5])
        if(adc_new>=adc_ex):
            tempxyz=adc_new-adc_ex
        else:
            tempxyz=adc_ex-adc_new
        if(tempxyz>0.025):
            count_adc=0
        else:
            count_adc=count_adc+1

    output_v=adc_new

    if(output_v>=output_v_ex):
        tempxyz=output_v-output_v_ex
    else:
        tempxyz=output_v_ex-output_v
    if(tempxyz>0.05):
        need_flash_lcd=True
        output_v_ex=output_v
    else:
        need_flash_lcd=False




    #print("+++++"+"x"+"++++")
    #print(time.monotonic_ns())
    #print("+++++"+"x"+"++++")
    if(output_v<=gnd_jiaozhun):
        output_v=0
        pwm.frequency = BEE_A
        beep_time[0]=time.monotonic_ns()
        beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
        boo_speaked=True
        debug_str="gndd"
    else:
        if(boo_speaked==True):
            if(gnd_jiaozhun<output_v<=float_jiaozhun):
                boo_speaked=False
                pwm.duty_cycle=2 ** 15
                if(0.8<=output_v):
                    pwm.frequency = BEE_F
                    beep_time[0]=time.monotonic_ns()
                    beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                    debug_str="08-24"
                elif(0.3<=output_v):
                    pwm.frequency = BEE_E
                    beep_time[0]=time.monotonic_ns()
                    beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                    debug_str="03-08"

                elif(0.2<=output_v):
                    pwm.frequency = BEE_D
                    beep_time[0]=time.monotonic_ns()
                    beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                    debug_str="02-03"

                elif(0.1<=output_v):
                    pwm.frequency = BEE_C
                    beep_time[0]=time.monotonic_ns()
                    beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                    debug_str="01-02"

                elif(gnd_jiaozhun<output_v):
                    pwm.frequency = BEE_B
                    beep_time[0]=time.monotonic_ns()
                    beep_time[1]=beep_time[0]+(BEEP_MS*1000000)
                    debug_str="00-01"




    if(output_v>float_jiaozhun):
        boo_speaked=True
        pwm.frequency = BEE_A
        pwm.duty_cycle = 0 #stop the beep
        debug_str="over "+str(float_jiaozhun)


    voice_check()
    if(need_flash_lcd==True):
        need_flash_lcd=False
        print('+++++++++')
        print(output_v)
        #print(debug_str)
        #print(pwm.frequency)
        print('+++++++++')
        ge=int(output_v)
        xiaoshu=output_v-ge

        output_v=('%.3f' % output_v)
        v_display= str(output_v)
        adc_samll_display = label.Label(terminalio.FONT, scale=2,text=v_display, color=0x33FFFF, x=30, y=20)


        #vbat_ad=('%.1f' % vbat_ad)
        bat_str=vbat_ad
        v_display= str(bat_str)
        v_display='BAT:'+v_display[0:3]
        display_bat_v= label.Label(terminalio.FONT, scale=2,text=v_display, color=0xFFFF00, x=150, y=20)


        str_ge=str(ge)+'.'
        xiaoshu=('%.3f' % xiaoshu)
        xiaoshu=str(xiaoshu)
        xiaoshu=xiaoshu[2:5]
        ge_big_display = label.Label(terminalio.FONT, scale=4,text=str_ge, color=0xFFCC00, x=10, y=130)
        xiaoshu_big_display = label.Label(terminalio.FONT, scale=10,text=xiaoshu, color=0xFFFFFF, x=65, y=110)


        v_lcd = displayio.Group()
        v_lcd.append(adc_samll_display)
        v_lcd.append(display_bat_v)
        v_lcd.append(ge_big_display)
        v_lcd.append(xiaoshu_big_display)
        display_lcd.show(v_lcd)

    time.sleep(0.01)
