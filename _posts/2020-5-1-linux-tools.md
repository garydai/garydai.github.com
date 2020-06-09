---
date: 2020-5-1
layout: default
title: Linux 性能分析工具

---

# Linux 性能分析工具



![image-20200501220458159](/Users/daitechang/Documents/garydai.github.com/_posts/pic/image-20200501220458159.png)

vmstat 1 1 上下文切换

pidstat -w -u 1 看哪个进程切换多

pidstat -wt 1 看哪个线程切换多

watch -d cat /proc/interrupts 中断使用情况，中断上下文切换情况

## 保留当前系统信息

（1）系统当前网络连接

```shell
ss -antp > $DUMP_DIR/ss.dump 2>&1
```

（2）网络状态统计

```shell
netstat -s > $DUMP_DIR/netstat-s.dump 2>&1

sar -n DEV 1 2 > $DUMP_DIR/sar-traffic.dump 2>&1
```

（3）进程资源

```shell
lsof -p $PID > $DUMP_DIR/lsof-$PID.dump
```

（4）CPU 资源

```shell
mpstat > $DUMP_DIR/mpstat.dump 2>&1
vmstat 1 3 > $DUMP_DIR/vmstat.dump 2>&1
sar -p ALL  > $DUMP_DIR/sar-cpu.dump  2>&1
uptime > $DUMP_DIR/uptime.dump 2>&1
```

（5）I/O 资源

```shell
iostat -x > $DUMP_DIR/iostat.dump 2>&1
```

（6）内存问题

```shell
free -h > $DUMP_DIR/free.dump 2>&1
```

（7）其他全局

```shell
ps -ef > $DUMP_DIR/ps.dump 2>&1
dmesg > $DUMP_DIR/dmesg.dump 2>&1
sysctl -a > $DUMP_DIR/sysctl.dump 2>&1
```

（8）进程快照，最后的遗言（jinfo）

```shell
${JDK_BIN}jinfo $PID > $DUMP_DIR/jinfo.dump 2>&1
```

（9）dump 堆信息

```shell
${JDK_BIN}jstat -gcutil $PID > $DUMP_DIR/jstat-gcutil.dump 2>&1
${JDK_BIN}jstat -gccapacity $PID > $DUMP_DIR/jstat-gccapacity.dump 2>&1
```

（10）堆信息

```shell
${JDK_BIN}jmap $PID > $DUMP_DIR/jmap.dump 2>&1
${JDK_BIN}jmap -heap $PID > $DUMP_DIR/jmap-heap.dump 2>&1
${JDK_BIN}jmap -histo $PID > $DUMP_DIR/jmap-histo.dump 2>&1
${JDK_BIN}jmap -dump:format=b,file=$DUMP_DIR/heap.bin $PID > /dev/null  2>&1
```

（11）JVM 执行栈

```shell
${JDK_BIN}jstack $PID > $DUMP_DIR/jstack.dump 2>&1
```

```shell
top -Hp $PID -b -n 1 -c >  $DUMP_DIR/top-$PID.dump 2>&1
```

（12）高级替补

```shell
kill -3 $PID
```

有时候，jstack 并不能够运行，有很多原因，比如 Java 进程几乎不响应了等之类的情况。我们会尝试向进程发送 kill -3 信号，这个信号将会打印 jstack 的 trace 信息到日志文件中，是 jstack 的一个替补方案。

```shell
gcore -o $DUMP_DIR/core $PID
```

对于 jmap 无法执行的问题，也有替补，那就是 GDB 组件中的 gcore，将会生成一个 core 文件。我们可以使用如下的命令去生成 dump：

```shell
${JDK_BIN}jhsdb jmap --exe ${JDK}java  --core $DUMP_DIR/core --binaryheap
```

3. 内存泄漏的现象

 jmap 命令，它在 9 版本里被干掉了，取而代之的是 jhsdb，你可以像下面的命令一样使用。

```shell
jhsdb jmap  --heap --pid  37340
jhsdb jmap  --pid  37288
jhsdb jmap  --histo --pid  37340
jhsdb jmap  --binaryheap --pid  37340
```




## 参考

https://kaiwu.lagou.com/course/courseInfo.htm?courseId=31#/detail/pc?id=1035