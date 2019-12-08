---
layout: default
title: keeplive
---



# keeplive

#### tcp

在使用TCP长连接（复用已建立TCP连接）的场景下，需要对TCP连接进行保活，避免被网关干掉连接。
在应用层，可以通过定时发送心跳包的方式实现。而Linux已提供的TCP KEEPALIVE，在应用层可不关心心跳包何时发送、发送什么内容，由OS管理：OS会在该TCP连接上定时发送探测包，探测包既起到**连接保活**的作用，也能自动检测连接的有效性，并**自动关闭无效连接**

**TCP Keepalive默认是关闭的**

建立TCP连接时，就有定时器与之绑定，其中的一些定时器就用于处理keepalive过程。当keepalive定时器到0的时候，便会给对端发送一个不包含数据部分的keepalive探测包（probe packet），如果收到了keepalive探测包的回复消息，那就可以断定连接依然是OK的。如果我们没有收到对端keepalive探测包的回复消息，我们便可以断定连接已经不可用，进而采取一些措施。

```
# cat /proc/sys/net/ipv4/tcp_keepalive_time
7200
# cat /proc/sys/net/ipv4/tcp_keepalive_intvl
75
# cat /proc/sys/net/ipv4/tcp_keepalive_probes
9
```

tcp_keepalive_time，在TCP保活打开的情况下，如果在该时间内没有数据往来，则发送探测包。即允许的持续空闲时长，或者说每次正常发送心跳的周期，默认值为7200s（2h）。
tcp_keepalive_probes 尝试探测的次数。如果发送的探测包次数超过该值仍然没有收到对方响应，则认为连接已失效并关闭连接。默认值为9（次）
tcp_keepalive_intvl，探测包发送间隔时间。默认值为75s。

###### TCP连接不活跃被干掉具体是什么

在三层地址转换中，我们可以保证局域网内主机向公网发出的IP报文能顺利到达目的主机，但是从目的主机返回的IP报文却不能准确送至指定局域网主机（我们不能让网关把IP报文广播至全部局域网主机，因为这样必然会带来安全和性能问题）。为了解决这个问题，网关路由器需要借助传输层端口，通常情况下是TCP或UDP端口，由此来生成一张**传输层端口转换表**。
由于**端口数量有**限（0~65535），端口转换表的维护占用系统资源，因此不能无休止地向端口转换表中增加记录。对于过期的记录，网关需要将其删除。如何判断哪些是过期记录？网关认为，一段时间内无活动的连接是过期的，应**定时检测转换表中的非活动连接，并将之丢弃**。

https://blog.chionlab.moe/2016/09/24/linux-tcp-keepalive/

#### http

在 HTTP 1.0 时期，每个 TCP 连接只会被一个 HTTP Transaction（请求加响应）使用，请求时建立，请求完成释放连接。当网页内容越来越复杂，包含大量图片、CSS 等资源之后，这种模式效率就显得太低了。所以，在 HTTP 1.1 中，引入了 HTTP persistent connection 的概念，也称为 HTTP keep-alive，目的是复用TCP连接，在一个TCP连接上进行多次的HTTP请求从而提高性能。

HTTP1.0中默认是关闭的，需要在HTTP头加入"Connection: Keep-Alive"，才能启用Keep-Alive；HTTP1.1中默认启用Keep-Alive，加入"Connection: close "，才关闭。



### reference

https://segmentfault.com/a/1190000012894416