BASE_EN=[':_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz']
def is_all_english(strs):
    for i in strs:
        if i not in BASE_EN:
            return False
    return True

def is_has_colon(strs):
    i=':'in strs
    return i



def open_cfg():
    cfglist=[]
    cfgdict={}
    fr = open('dadc_config.txt', 'r')
    results = fr.read().splitlines()
    for line in results:
        if(is_has_colon(line)):
            cfglist.append(line)
    fr.close()
    for x in cfglist:
        mv=x.split(':',1)
        cfgdict[mv[0]]=mv[1]
    #print(cfgdict)
    return cfgdict
