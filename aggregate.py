# -*- coding: utf-8 -*-

import csv, json
import sys, codecs
import prettytable
from mongoengine import connect
from mongoengine import Document, StringField, LongField, DictField, ListField

db = "alex"
alias = db
host = "10.23.102.140"

useless = ['SIGN', 'OrderNo']

if sys.stdout.encoding != 'UTF-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'UTF-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

class JmeterLogs(Document):
    jobname = StringField(required=True)
    state   = StringField(required=True)
    metricslist = ListField(DictField(required=True))
    startts = LongField(required=True)
    endts   = LongField(required=True)
    meta = {'db_alias': alias}

def setTimeStatistic(metrics, timeStamp, elapsed, code):
    if not metrics.get("timeMetrics"):
        metrics["timeMetrics"] = {}
    timeMetrics = metrics["timeMetrics"]

    timeIndex = str(int((timeStamp+999)/1000))
    if not timeMetrics.get(timeIndex):
        timeMetrics[timeIndex] = {"elapsed": [{"totalelapsed": 0, "num": 0}, {"totalelapsed": 0, "num": 0}], "tps": {}}
    elapsedIndex = int((timeStamp%1000)/500)
    timeMetrics[timeIndex]["elapsed"][elapsedIndex]["num"] += 1 # 500毫米内请求个数
    timeMetrics[timeIndex]["elapsed"][elapsedIndex]["totalelapsed"] += elapsed # 累加500毫秒费时
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


metrics = {}
with open('res.jtl', 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        label = row["label"]
        if label not in useless:
            aggregate(metrics, label, row)
            aggregate(metrics, "Total", row)
            setTimeStatistic(metrics[label], int(row["timeStamp"]), int(row["elapsed"]), row["responseCode"])

metrics_list = []
data = prettytable.PrettyTable(["Label", "Number", "Average", "Median", "90%Line", "95%Line", "99%Line", "Min", "Max", "Error%", "QPS", "KB/sec"])
od = sorted(metrics.items())
for (key, value) in od:
    success = value["success"]
    elapsed_list = sorted(value["elapsed"])
    total = len(elapsed_list)
    elapsedtime = float(value["stopTime"])/1000 - float(value["startTime"])/1000
    average = float("%.2f" %(float(sum(elapsed_list))/float(total)))
    errRate = float("%.2f" %(float(total-success)*100.0/float(total)))
    p50 = elapsed_list[int(total/2-1)]
    p90 = elapsed_list[int(total*0.9)-1]
    p95 = elapsed_list[int(total*0.95)-1]
    p99 = elapsed_list[int(total*0.99)-1]
    mini = elapsed_list[0]
    maxi = elapsed_list[-1]
    qps = float("%.1f" %(float(total)/float(elapsedtime)))
    total_bytes = value["bytes"]
    kbs = float("%.1f" %(float(total_bytes)/(1024*float(elapsedtime))))
    data.add_row([key, total, average, p50, p90, p95, p99, mini, maxi, errRate, qps, kbs])

    m = {
        "label": key,
        "total": total,
        "latencies": {
            "average": average,
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "p99": p99,
            "min": mini,
            "max": maxi
        },
        "errorrate": errRate,
        "qps": qps,
        "kbs": kbs,
        "starttime": value["startTime"],
        "stoptime": value["stopTime"],
        "timemetrics": value.get("timeMetrics")
    }
    metrics_list.append(m)

#print(data.get_string(sortby="Label", reversesort=True))
print(data)


connect(db, alias=alias, host=host)
jmeterLog = JmeterLogs(jobname="eyotang_load_test", state="Finished", metricslist=metrics_list, startts=metrics["Total"]["startTime"]/1000, endts=metrics["Total"]["stopTime"]/1000)
jmeterLog.save()

