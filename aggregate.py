# -*- coding: utf-8 -*-

import csv
import sys, codecs
import prettytable
from mongoengine import connect
from mongoengine import Document, StringField, DictField

db = "jmeter"
alias = db
host = "10.23.102.140"

if sys.stdout.encoding != 'UTF-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'UTF-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

class JmeterLog(Document):
    jobname = StringField(required=True)
    metrics = DictField()
    meta = {'db_alias': alias}

def setTimeStatistic(metrics, timeStamp, elapsed, code):
    if not metrics.get("timeMetrics"):
        metrics["timeMetrics"] = {}
    timeMetrics = metrics["timeMetrics"]

    timeIndex = str(int((timeStamp+999)/1000))
    if not timeMetrics.get(timeIndex):
        timeMetrics[timeIndex] = {"elapsed": [[0, 0], [0, 0]], "tps": {}}
    elapsedIndex = int((timeStamp%1000)/500)
    timeMetrics[timeIndex]["elapsed"][elapsedIndex][1] += 1 # 500毫米内请求个数
    timeMetrics[timeIndex]["elapsed"][elapsedIndex][0] += elapsed # 累加500毫秒费时
    if not timeMetrics[timeIndex]["tps"].get(code):
        timeMetrics[timeIndex]["tps"][code] = 0
    timeMetrics[timeIndex]["tps"][code] += 1
    return timeMetrics

def aggregate(metrics, label, row):
    if not metrics.get(label):
        metrics[label] = {"success": 0, "elapsed": [], "startTime": sys.maxsize, "stopTime": 0, "bytes": 0}
    m = metrics[label]
    m["elapsed"].append(int(row["elapsed"]))
    success = row["success"]
    if success == "true":
        m["success"] += 1

    timeStamp = int(row["timeStamp"])
    if m["startTime"] > timeStamp:
        m["startTime"] = timeStamp
    if m["stopTime"] < timeStamp:
        m["stopTime"] = timeStamp
    m["bytes"] += int(row["bytes"])


useless = ['SIGN', 'OrderNo']
metrics = {}
with open('res.jtl', 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        label = row["label"]
        if label not in useless:
            aggregate(metrics, label, row)
            aggregate(metrics, "Total", row)
            setTimeStatistic(metrics[label], int(row["timeStamp"]), int(row["elapsed"]), row["responseCode"])

connect(db, alias=alias, host=host)
jmeterLog = JmeterLog(jobname="eyotang_load_test", metrics=metrics)
jmeterLog.save()

data = prettytable.PrettyTable(["Label", "Number", "Average", "Median", "90%Line", "95%Line", "99%Line", "Min", "Max", "Error%", "QPS", "KB/sec"])
for key, value in metrics.items():
    success = value["success"]
    elapsed_list = sorted(value["elapsed"])
    total = len(elapsed_list)
    elapsedtime = float(value["stopTime"])/1000 - float(value["startTime"])/1000
    average = float("%.2f" %(float(sum(elapsed_list))/float(total)))
    errRate = float("%.2f" %(float(total-success)*100.0/float(total)))
    qps = float("%.1f" %(float(total)/float(elapsedtime)))
    kbs = float("%.1f" %(float(value["bytes"])/(1024*float(elapsedtime))))
    data.add_row([key, total, average, elapsed_list[int(total/2-1)], elapsed_list[int(total*0.9)-1], elapsed_list[int(total*0.95)-1], elapsed_list[int(total*0.99)-1], elapsed_list[0], elapsed_list[-1], errRate, qps, kbs])

print(data.get_string(sortby="Label", reversesort=True))

