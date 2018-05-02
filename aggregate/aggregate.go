package main

import (
	"flag"
	"fmt"
	"github.com/eyotang/prettytable/prettytable"
	"io/ioutil"
	"os"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

type JmeterMetrics struct {
	startTime    uint64
	stopTime     uint64
	elapsed      []int
	totalElapsed uint64
	success      uint64
	bytes        uint64
}

type Config struct {
	logs     []string
	discards []string
}

const (
	TS         = 0
	ELAPSED    = 1
	LABEL      = 2
	SUCCESS    = 7
	BYTES      = 9
	MAX_FIELDS = 14 // 标准jtl文件为14个域
	UINT64_MAX = ^uint64(0)
	MAX_LABEL  = 24 // 英文占1个字符，中文占2个字符
)

func inSlice(slice []string, s string) bool {
	for _, k := range slice {
		if k == s {
			return true
		}
	}
	return false
}

func defaultMerics() *JmeterMetrics {
	return &JmeterMetrics{
		stopTime:  0,
		startTime: UINT64_MAX,
	}
}

func aggregate(metrics map[string]*JmeterMetrics, label string, record []string) error {
	var (
		timeStamp uint64
		elapsed   int
		bytes     uint64
		success   string
	)

	if _, ok := metrics[label]; !ok { // 不存在，先给个默认值
		metrics[label] = defaultMerics()
	}

	timeStamp, err := strconv.ParseUint(record[TS], 10, 64)
	if err != nil {
		fmt.Println("Error:", err)
		return err
	}
	elapsed, err = strconv.Atoi(record[ELAPSED])
	if err != nil {
		fmt.Println("Error:", err)
		return err
	}
	bytes, err = strconv.ParseUint(record[BYTES], 10, 64)
	if err != nil {
		fmt.Println("Error:", err)
		return err
	}

	m := metrics[label]
	if m.startTime > timeStamp {
		m.startTime = timeStamp
	}
	if m.stopTime < timeStamp {
		m.stopTime = timeStamp
	}
	m.elapsed = append(m.elapsed, elapsed)
	m.totalElapsed += uint64(elapsed)
	m.bytes += bytes

	success = record[SUCCESS]
	if success == "true" {
		m.success++
	}

	return nil
}

var g_config Config

func parseArgs() {
	var (
		logArg     string
		discardArg string
		logs       []string
		discards   []string
	)
	flag.StringVar(&logArg, "l", "res.jtl", "Jmeter jtl files. eg: res.jtl, res2.jtl")
	flag.StringVar(&discardArg, "d", "SIGN, OrderNo", "Discard labels (divided by ',').")
	flag.Parse()

	logs = strings.Split(logArg, ",")
	discards = strings.Split(discardArg, ",")
	for _, log := range logs {
		g_config.logs = append(g_config.logs, strings.TrimSpace(log))
	}
	if 0 == len(g_config.logs) {
		g_config.discards = append(g_config.discards, "res.jtl")
	}

	for _, discard := range discards {
		g_config.discards = append(g_config.discards, strings.TrimSpace(discard))
	}

	USELESS := []string{"SIGN", "OrderNo"}
	g_config.discards = append(USELESS, g_config.discards...)
}

func truncate(name string, fixed int) string {
	var total int
	var index int
	var delta int
	var last int
	nameRune := []rune(name)
	for _, r := range name {
		last = delta
		if unicode.Is(unicode.Scripts["Han"], r) {
			delta = 2
		} else {
			delta = 1
		}
		total += delta

		if total-fixed == 2 {
			if last == 2 {
				return string(nameRune[:index-1]) + ".."
			} else {
				return string(nameRune[:index-2]) + ".."
			}
		}
		if total-fixed == 1 {
			if delta == 2 {
				return string(nameRune[:index-1]) + ".."
			} else {
				if last == 2 {
					return string(nameRune[:index-1]) + ".."
				} else {
					return string(nameRune[:index-2]) + ".."
				}
			}
		}

		index++
	}
	return name
}

func main() {
	var (
		metrics  map[string]*JmeterMetrics
		label    string
		total    uint64
		duration float64
		average  float64
		errRate  float64
		qps      float64
		kbs      float64
		header   []string
		row      []string
		table    [][]string
	)

	parseArgs()

	metrics = make(map[string]*JmeterMetrics)
	for _, log := range g_config.logs {
		file, err := os.Open(log)
		if err != nil {
			fmt.Println("Error:", err)
			return
		}
		defer file.Close()

		fd, err := ioutil.ReadAll(file)
		if err != nil {
			fmt.Println("Error:", err)
			return
		}
		content := string(fd)
		lines := strings.Split(content, "\n")
		for _, line := range lines[1:] {
			record := strings.Split(line, ",")
			if len(record) != MAX_FIELDS {
				continue
			}

			label = record[LABEL]
			if inSlice(g_config.discards, label) {
				continue
			}

			aggregate(metrics, label, record)
		}
	}

	keys := []string{"Total"}
	for k := range metrics {
		keys = append(keys, k)
	}
	sort.Strings(keys[1:])

	t := defaultMerics()
	for _, m := range metrics {
		if t.startTime > m.startTime {
			t.startTime = m.startTime
		}
		if t.stopTime < m.stopTime {
			t.stopTime = m.stopTime
		}
		t.elapsed = append(t.elapsed, m.elapsed...)
		t.totalElapsed += m.totalElapsed
		t.bytes += m.bytes
		t.success += m.success
	}
	metrics["Total"] = t

	for _, label := range keys {
		m := metrics[label]
		sort.Ints(m.elapsed)
		total = uint64(len(m.elapsed))
		duration = float64(m.stopTime-m.startTime) / 1000
		average = float64(float64(m.totalElapsed) / float64(total))
		errRate = float64(float64(total-m.success) * 100.0 / float64(total))
		qps = float64(float64(total) / float64(duration))
		kbs = float64(float64(m.bytes) / float64(1024*duration))
		row = []string{
			truncate(label, MAX_LABEL),
			strconv.FormatUint(total, 10),
			strconv.FormatFloat(average, 'f', 2, 64),
			strconv.Itoa(m.elapsed[total/2-1]),
			strconv.Itoa(m.elapsed[total*9/10-1]),
			strconv.Itoa(m.elapsed[total*95/100-1]),
			strconv.Itoa(m.elapsed[total*99/100-1]),
			strconv.Itoa(m.elapsed[0]),
			strconv.Itoa(m.elapsed[total-1]),
			strconv.FormatFloat(errRate, 'f', 2, 64),
			strconv.FormatFloat(qps, 'f', 1, 64),
			strconv.FormatFloat(kbs, 'f', 1, 64),
		}
		table = append(table, row)
	}

	header = []string{"接口名称", "请求数", "平均耗时ms", "中分位", "90分位", "95分位", "99分位", "Min", "Max", "错误率%", "QPS", "KB/sec"}
	prettytable.PrintTable(header, table)
}
