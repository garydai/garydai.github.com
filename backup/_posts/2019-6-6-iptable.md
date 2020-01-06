---
layout: default

title: iptables

---

## iptables


### iptables
![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/iptables.png)

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/iptables2.png)



filter表：负责过滤功能，防火墙；内核模块：iptables_filter

nat表：network address translation，网络地址转换功能；内核模块：iptable_nat

mangle表：拆解报文，做出修改，并重新封装 的功能；iptable_mangle

raw表：关闭nat表上启用的连接追踪机制；iptable_raw



PREROUTING    的规则可以存在于：raw表，mangle表，nat表。

INPUT      的规则可以存在于：mangle表，filter表，（centos7中还有nat表，centos6中没有）。

FORWARD     的规则可以存在于：mangle表，filter表。

OUTPUT     的规则可以存在于：raw表mangle表，nat表，filter表。

POSTROUTING    的规则可以存在于：mangle表，nat表。



### docker

#### 容器对外请求数据

如果Docker0中的容器请求外部的数据，那么他的数据包将会发送到网关172.17.0.1处。当数据包到达网关后，将会查询主机的路由表，确定数据包将从那个网卡发出。iptables负责对数据包进行snat转换，将原地址转为对应网卡的地址，因此容器对外是不可见的。

#### 外部对容器请求数据

外部想要访问容器内的数据，首先需要将容器的端口映射到宿主机上。这时候docker会在iptables添加转发规则，把接收到的数据转发给容器。


![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/iptables3.png)


![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/iptables4.png)

### reference
https://www.zsythink.net/archives/1199

nathttps://blog.csdn.net/jk110333/article/details/8229828