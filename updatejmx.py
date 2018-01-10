# -*- coding: utf-8 -*-

#import xml.etree.ElementTree as ET
from lxml import etree as ET

THREADS_TAG = "kg.apc.jmeter.threads.UltimateThreadGroup"
TPS_TAG = "kg.apc.jmeter.timers.VariableThroughputTimer"
THREADS_ATTRIB = "ultimatethreadgroupdata"
TPS_ATTRIB = "load_profile"

THREADS_CFG_TPL = {
    'collectionProp': -2081808454,
    'tpl': {
        'startThreads': 100,
        'initialDelay': 0,
        'startupTime': 30,
        'holdLoad': 60,
        'shutdownTime': 10
    }
}

TPS_CFG_TPL = {
    'collectionProp': 1800738992,
    'tpl': {
        'startRps': 1,
        'endRps': 1000,
        'duration': 60
    }
}

threads_cfgs = [
    {
        'startThreads': 50,
        'initialDelay': 0,
        'startupTime': 30,
        'holdLoad': 30,
        'shutdownTime': 20
    },
    {
        'startThreads': 100,
        'initialDelay': 0,
        'startupTime': 30,
        'holdLoad': 60,
        'shutdownTime': 10
    }
]

tps_cfgs = [
    {
        'startRps': 2,
        'endRps': 1000,
        'duration': 60
    },
    {
        'startRps': 1,
        'endRps': 200,
        'duration': 30
    }
]

parser = ET.XMLParser(remove_blank_text=True)
tree = ET.parse('tmpl.jmx', parser)
root = tree.getroot()

def searchByTag(node, tag):
    if node.tag == tag:
        return node
    else:
        for child in node:
            target = searchByTag(child, tag)
            if target is not None:
                return target


thread = searchByTag(root, THREADS_TAG)
tps = searchByTag(root, TPS_TAG)

def removeChildren(node, attribName):
    target = node.find(".//*[@name='%s']" %(attribName))
    children = list(target)
    for child in children:
        target.remove(child)

removeChildren(thread, THREADS_ATTRIB)
removeChildren(tps, TPS_ATTRIB)

def addChildren(node, attribName, cfgTpl, cfgs):
    target = node.find(".//*[@name='%s']" %(attribName))
    collection = str(cfgTpl.get('collectionProp'))
    tpl = cfgTpl.get('tpl')
    for cfg in cfgs:
        child = ET.SubElement(target, 'collectionProp', {'name': collection})
        for k, v in tpl.items(): # 按照模板填充，没有的项填充默认值
            val = cfg.get(k)
            if val is None:
                val = v
            c = ET.SubElement(child, 'stringProp', {'name': str(v)})
            c.text = str(val)

addChildren(thread, THREADS_ATTRIB, THREADS_CFG_TPL, threads_cfgs)
addChildren(tps, TPS_ATTRIB, TPS_CFG_TPL, tps_cfgs)

tree.write('result.jmx', pretty_print=True, encoding='utf-8')
