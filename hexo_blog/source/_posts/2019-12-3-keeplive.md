---
date: 2019-12-3
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

#### http

在 HTTP 1.0 时期，每个 TCP 连接只会被一个 HTTP Transaction（请求加响应）使用，请求时建立，请求完成释放连接。当网页内容越来越复杂，包含大量图片、CSS 等资源之后，这种模式效率就显得太低了。所以，在 HTTP 1.1 中，引入了 HTTP persistent connection 的概念，也称为 HTTP keep-alive，目的是复用TCP连接，在一个TCP连接上进行多次的HTTP请求从而提高性能。

HTTP1.0中默认是关闭的，需要在HTTP头加入"Connection: Keep-Alive"，才能启用Keep-Alive；HTTP1.1中默认启用Keep-Alive，加入"Connection: close "，才关闭。

###### 例子

1. 客户端浏览器向 `www.bilibili.com:80` 建立TCP连接，并在此TCP连接上传输七层报文，请求`GET /index.html`资源，在请求头中，`Connection`置为`keep-alive`。
2. 服务端向浏览器返回`index.html`的文件内容，响应报头中`Connection`置为`keep-alive`，随后，**不关闭和客户端的TCP连接**。
3. 客户端复用该TCP连接，并请求`GET /style.css`资源，请求头置`Connection`为`keep-alive`。
4. 服务器向浏览器返回`index.css`文件内容，仍然不关闭该TCP连接。
5. 客户端继续复用该TCP连接请求多个同域资源。
6. 客户端所需的各种资源都请求完毕，但是因为客户端的最后一次资源请求头中仍置`Connection`为`keep-alive`，该TCP连接仍未被关闭。
7. 如果在一段时间（通常是3分钟左右）内客户端没有使用该TCP连接请求资源，服务器可能会关闭该连接。连接被关闭后，客户端需要重新向该域建立TCP连接才能继续请求数据。



Chrome对于可复用的TCP连接，采用的保活机制是TCP层（传输层）自带的Keepalive机制，通过TCP Keepalive探测包的方式实现，而不是在七层报文上自成协议来传输其它数据。

而实际上，由于HTTP1.1对时序和报文的约定，浏览器也不可在七层实现保活。假设，客户端在通过HTTP1.1获取一次资源后，若在这个TCP连接上发送一个`0x70`（无意义的数据，在七层实现保活的方式大多如此），服务器会在应用层接收到并缓存该数据，一段时间后客户端发送有效的HTTP请求报头，则服务端CGI应用程序收到的数据是`0x70`再接上一段HTTP请求头，这被认为是无效的HTTP报文，服务器则会返回400响应头，告知客户端这是坏的请求（Bad Request）。

所以，浏览器在处理HTTP1.1请求所对应的TCP连接的保活时，通过使用TCP Keepalive机制，来避免污染七层（应用层）的传输数据。

### reference

https://segmentfault.com/a/1190000012894416

https://blog.chionlab.moe/2016/11/07/tcp-keepalive-on-chrome/

https://blog.chionlab.moe/2016/09/24/linux-tcp-keepalive/