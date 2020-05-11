---
date: 2020-1-20
layout: default
title: docker
---

# docker

## Cgroup

资源控制

![image-20200412203739705](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200412203739705.png)

cgroup 是一种特殊的文件系统

```c

struct file_system_type cgroup_fs_type = {
  .name = "cgroup",
  .mount = cgroup_mount,
  .kill_sb = cgroup_kill_sb,
  .fs_flags = FS_USERNS_MOUNT,
};
```



## namespace

访问隔离

### Network Namespace

![image-20200502110410734](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200502110410734.png)

![image-20200504221717312](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200504221717312.png)

由于容器运行在自己单独的network namespace里面，所以都有自己单独的协议栈，情况和上面的虚拟机差不多，但它采用了另一种方式来和外界通信

发出去的数据包先到达br0，然后交给host机器的协议栈，由于目的IP是外网IP，且host机器开启了IP forward功能，于是数据包会通过eth0发送出去，由于.9.1是内网IP，所以一般发出去之前会先做NAT转换（NAT转换和IP forward功能都需要自己配置）。由于要经过host机器的协议栈，并且还要做NAT转换，所以性能没有上面虚拟机那种方案好，优点是容器处于内网中，安全性相对要高点。（由于数据包统一由IP层从eth0转发出去，所以不存在mac地址的问题，在无线网络环境下也工作良好）

![image-20200504221914485](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200504221914485.png)

虚拟机通过tun/tap或者其它类似的虚拟网络设备，将虚拟机内的网卡同br0连接起来，这样就达到和真实交换机一样的效果，虚拟机发出去的数据包先到达br0，然后由br0交给eth0发送出去，数据包都不需要经过host机器的协议栈，效率高。

## rootfs

文件系统隔离。镜像的本质就是一个rootfs文件

## 容器引擎

生命周期控制

## 容器网络

Linux 容器能看见的“网络栈”，实际上是被隔离在它自己的 Network Namespace 当中的

而所谓“网络栈”，就包括了：网卡（Network Interface）、回环设备（Loopback Device）、路由表（Routing Table）和 iptables 规则。对于一个进程来说，这些要素，其实就构成了它发起和响应网络请求的基本环境

作为一个容器，它可以声明直接使用宿主机的网络栈（–net=host），即：不开启 Network Namespace

```shell
$ docker run –d –net=host --name nginx-host nginx
```

像这样直接使用宿主机网络栈的方式，虽然可以为容器提供良好的网络性能，但也会不可避免地引入共享网络资源的问题，比如端口冲突。所以，在大多数情况下，我们都希望容器进程能使用自己 Network Namespace 里的网络栈，即：拥有属于自己的 IP 地址和端口

如果你想要实现两台主机之间的通信，最直接的办法，就是把它们用一根网线连接起来；而如果你想要实现多台主机之间的通信，那就需要用网线，把它们连接在一台交换机上

在 Linux 中，能够起到虚拟交换机作用的网络设备，是网桥（Bridge）。它是一个工作在数据链路层（Data Link）的设备，主要功能是根据 MAC 地址学习来将数据包转发到网桥的不同端口（Port）上。

Docker 项目会默认在宿主机上创建一个名叫 docker0 的网桥，凡是连接在 docker0 网桥上的容器，就可以通过它来进行通信。可是，我们又该如何把这些容器“连接”到 docker0 网桥上呢？这时候，我们就需要使用一种名叫 Veth Pair 的虚拟设备

Veth Pair 设备的特点是：它被创建出来后，总是以两张虚拟网卡（Veth Peer）的形式成对出现的。并且，从其中一个“网卡”发出的数据包，可以直接出现在与它对应的另一张“网卡”上，哪怕这两个“网卡”在不同的 Network Namespace 里

## 参考

https://coolshell.cn/articles/17010.html

https://time.geekbang.org/column/article/115582