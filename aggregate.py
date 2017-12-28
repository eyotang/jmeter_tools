# -*- coding: utf-8 -*-

import csv
import sys
import prettytable

useless = ['SIGN', 'OrderNo']
metrics = {}

with open('res.jtl', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        label = row["label"]
        if label not in useless:
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
    data.add_row([key, total, average, elapsed_list[total/2-1], elapsed_list[int(total*0.9)-1], elapsed_list[int(total*0.95)-1], elapsed_list[int(total*0.99)-1], elapsed_list[0], elapsed_list[-1], errRate, qps, kbs])

print(data)

