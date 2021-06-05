---
date: 2021-6-2
layout: default
title: tcp retries
---

# tcp retries

项目中连接池hirika 执行SQL超时15分钟

![image-20210602205427258](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210602205427258.png)

connection timeout设置成30s，但是超时了15分钟



可以确定连接被断开了，tcp再不断重传。因为被断开，statement开启的超时线程，是发送kill query命令到数据库，连接都断了，这个超时线程的作用没用，所以30s超时不起作用

真的要设置超时，应该要在jdbc url上设置socket timeout，但是设置太短会影响有些长时间的sql语句



![image-20210603064656987](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210603064656987.png)

*默认sysctl_tcp_retries2=15，timeout=1023*TCP_RTO_MIN+6*TCP_RTO_MAX=920.6s，约15分钟



防火墙会定时与不定时的删除 TCP 会话，在会话删除后，Java服务器使用连接池的连接发送数据库查询请求，过程如下：

1. Java服务器建立连接池，经由防火墙与数据库建立三次握手的请求
2. 此时防火墙认可这些连接，会正常转发这些请求
3. 某时刻，防火墙删除此连接，不会发送 ASK 与 FIN 包
4. Java服务器使用此连接发送数据库请求
5. 防火墙收到请求后发现此连接无效，丢弃网络包，并且不会发送 ASK 包
6. Java服务器在2*RTT后判定网络包丢失，因为没收到 SDK，所以默认判定网络发生拥塞
7. 在系统设定的退避时到达后，再次发送重试包，如此循环，退避时间会随着重试次数的增加而增加
8. 当重试次数到达系统设定上限后，（Linux 默认次数为15次），重新发起三次握手连接。



重试次数和超时时间对应关系

![image-20210603055925154](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210603055925154.png)



调整**/proc/sys/net/ipv4/tcp_retries2** 参数来减少重试次数，当网络环境较好时，可以减少到 5~6 次。

https://blog.csdn.net/u014155356/article/details/82865451

https://www.jianshu.com/p/29ea5ed5cb9f





