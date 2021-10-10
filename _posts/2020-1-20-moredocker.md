---
date: 2020-1-20
layout: default
title: docker
---

# docker

![image-20210319122541722](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210319122541722.png)

1. runC是最常用的 容器低层运行时，不包含镜像管理，它假定容器的文件包已经从镜像里解压出来并存放于文件系统中。runC 创建的容器需要手动配置网络才能与其他容器或者网络节点连通。 ——**镜像并不是运行容器所必须的**。
2. containerd是最常用的 容器高层运行时，提供镜像下载、解压等功能， 不包含镜像构建、上传等功能
3. 再往上，Docker 提供了许多 UX 增强功能，比如ps/system prune 这些。 UX 增强的功能并不是 Kubernetes 所必须的

![image-20210319121248469](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210319121248469.png)

1. dockerd 是docker-containerd 的父进程， docker-containerd 是n个docker-containerd-shim 的父进程。
2. Containerd 是一个 gRPC 的服务器。它会在接到 docker daemon 的远程请 求之后，新建一个线程去处理这次请求。依靠 runC 去创建容器进程。而在容器启动之后， runC 进程会退出。
3. runC 命令，是 libcontainer 的一个简单的封装。这个工具可以 用来管理单个容器，比如容器创建，或者容器删除。

```
systemd(1)-+-NetworkManager(4700)-+-dhclient(13711)
           |-dockerd(5934)-+-containerd(5957)-+-containerd-shim(1672)-+-java(1689)-+-{java}(1725)
           |               |                  |                       |            |-{java}(1732)
           |               |                  |-containerd-shim(2465)-+-sh(2484)---java(2542)-+-{java}(2551)
           |               |                  |                       |                       |-{java}(2552)
           |               |                  |                       |                       |-{java}(2553)
           |               |                  |                       |                       |-{java}(2554)
```



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

### 网络模型

CNM

![image-20200624111438806](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200624111438806.png)

![image-20200623161402200](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200623161402200.png)

![image-20200623171837963](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200623171837963.png)

**CNM 中的 3 个核心组件如下**

- **沙盒**：一个沙盒包含了一个容器网络栈的信息。沙盒可以对容器的接口(interface)、路由和 DNS 设置等进行管理。沙盒的实现可以是 Linux network namespace、FreeBSD Jail 或者类似的机制。一个沙盒可以有多个端点和多个网络。
- **端点**：一个端点可以加入一个沙盒和一个网络。端点的实现可以是 veth pair、Open vSwitch 内部端口或者相似的设备。一个端点可以属于一个网络并且只属于一个沙盒。
- **网络**：一个网络是一组可以直接互相联通的端点。网络的实现可以是 Linux bridge、VLAN等。一个网络可以包含多个端点。

**Libnetwork 中的 5 中内置驱动如下**
**bridge 驱动**：这是 docker 设置的默认驱动。当使用 bridge 驱动时，libnetwork 将创建出来的 docker 容器连接到 docker0 网桥上。对于单机模式，bridge 驱动已经可以满足基本的需求了。但是这种模式下容器使用 NAT 方式与外界通信，这就增加了通信的复杂性。
**host 驱动**：使用 host 驱动的时候，libnetwork 不会为容器创建网络协议栈，即不会创建独立的 network namespace。Docker 容器中的进程处于宿主机的网络环境中，相当于容器和宿主机共用同一个 network namespace，容器共享使用宿主机的网卡、IP 和端口等资源。Host 模式很好的解决了容器与外界通信的地址转换问题，可以直接使用宿主机的 IP 进行通信，不存在虚拟化网络带来的开销。但是 host 驱动也降低了容器与容器之间、容器与宿主机之间网络的隔离性，引起网络资源的竞争和冲突。因此可以认为 host 驱动适用于对容器集群规模不大的场景。
**overlay 驱动**：overlay 驱动采用 IETF 标准的 VXLAN 方式，并且是 VXLAN 中被普遍认为最适合大规模的云计算虚拟化环境的 SDN controller 模式。在使用的过程中，还需要一个额外的配置存储服务，比如 Consul、etcd 或 ZooKeeper 等。并且在启动 docker daemon 的时候需要添加额外的参数来指定所使用的配置存储服务地址。
**remote 驱动**：这个驱动实际上并未做真正的网络服务实现，而是调用了用户自行实现的网络驱动插件，是 libnetwork 实现了驱动的插件化，更好地满足了用户的多样化需求。用户只要根据 libnetwork 提供的协议标准实现其接口并注册即可。
**null 驱动**：使用这种驱动的时候，docker 容器拥有字段的 network namespace，但是并不为 docker 容器进行任何网络配置。也就是说，这个容器除了 network namespace 自带的 loopback 网卡外，没有任何其它网卡、IP、路由等信息，需要用户为该容器添加网卡、配置 IP 等。这种模式如果不进行特定的配置是无法正常使用网络的，但是优点也非常明显，它给了用户最大的自由度来自定义容器的网络环境。

## 

Linux 容器能看见的“网络栈”，实际上是被隔离在它自己的 Network Namespace 当中的

而所谓“网络栈”，就包括了：网卡（Network Interface）、回环设备（Loopback Device）、路由表（Routing Table）和 iptables 规则。对于一个进程来说，这些要素，其实就构成了它发起和响应网络请求的基本环境

作为一个容器，它可以声明直接使用宿主机的网络栈（–net=host），即：不开启 Network Namespace

```shell
$ docker run –d –net=host --name nginx-host nginx
```

像这样直接使用宿主机网络栈的方式，虽然可以为容器提供良好的网络性能，但也会不可避免地引入共享网络资源的问题，比如端口冲突。所以，在大多数情况下，我们都希望容器进程能使用自己 Network Namespace 里的网络栈，即：拥有属于自己的 IP 地址和端口

如果你想要实现两台主机之间的通信，最直接的办法，就是把它们用一根网线连接起来；而如果你想要实现多台主机之间的通信，那就需要用网线，把它们连接在一台交换机上

在 Linux 中，能够起到虚拟交换机作用的网络设备，是网桥（Bridge）。它是一个工作在数据链路层（Data Link）的设备，主要功能是根据 MAC 地址学习来将数据包转发到网桥的不同端口（Port）上。

**Docker 项目会默认在宿主机上创建一个名叫 docker0 的网桥，凡是连接在 docker0 网桥上的容器，就可以通过它来进行通信。可是，我们又该如何把这些容器“连接”到 docker0 网桥上呢？这时候，我们就需要使用一种名叫 Veth Pair 的虚拟设备**

**Veth Pair 设备的特点是：它被创建出来后，总是以两张虚拟网卡（Veth Peer）的形式成对出现的。并且，从其中一个“网卡”发出的数据包，可以直接出现在与它对应的另一张“网卡”上，哪怕这两个“网卡”在不同的 Network Namespace 里**

**被限制在 Network Namespace 里的容器进程，实际上是通过 Veth Pair 设备 + 宿主机网桥的方式，实现了跟同其他容器的数据交换**
正是因为这样的特点，Veth Pair成对出现，很像是一对以太网卡，常常被看做是不同Network Namespace直连的“网线”。在Veth一端发送数据时，他会将数据发送到另一端并触发另一端的接收操作。我们可以把Veth Pair其中一端看做另一端的一个Peer。

![image-20210928082334953](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210928082334953.png)

### 跨主机网络（容器东西向流量）

- 思路一：修改底层网络设备配置，加入容器网络IP地址的管理，修改路由器网关等，该方式主要和SDN结合。

- 思路二：完全不修改底层网络设备配置，复用原有的underlay平面网络，解决容器跨主机通信，主要有如下两种方式：

- - Overlay隧道传输。把容器的数据包封装到原主机网络的三层或者四层数据包中，然后使用原来的网络使用IP或者TCP/UDP传输到目标主机，目标主机再拆包转发给容器。Overlay隧道如Vxlan、ipip等，目前使用Overlay技术的主流容器网络如Flannel、Weave等。
  - 修改主机路由。把容器网络加到主机路由表中，把主机当作容器网关，通过路由规则转发到指定的主机，实现容器的三层互通。目前通过路由技术实现容器跨主机通信的网络如Flannel host-gw、Calico等。

- 

![image-20200511102228168](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511102228168.png)

我们需要在已有的宿主机网络上，再通过软件构建一个覆盖在已有宿主机网络之上的、可以把所有容器连通在一起的虚拟网络。所以，这种技术就被称为：**Overlay Network（覆盖网络）**

而这个 Overlay Network 本身，可以由每台宿主机上的一个“特殊网桥”共同组成。比如，当 Node 1 上的 Container 1 要访问 Node 2 上的 Container 3 的时候，Node 1 上的“特殊网桥”在收到数据包之后，能够通过某种方式，把数据包发送到正确的宿主机，比如 Node 2 上。而 Node 2 上的“特殊网桥”在收到数据包后，也能够通过某种方式，把数据包转发给正确的容器，比如 Container 3。甚至，每台宿主机上，都不需要有一个这种特殊的网桥，而仅仅通过某种方式配置宿主机的路由表，就能够把数据包转发到正确的宿主机上

#### Flannel

三种实现

##### host-gw

##### UDP

性能最差的一种方式。所以，这个模式目前已经被弃用

```shell

# 在Node 1上
$ ip route
default via 10.168.0.1 dev eth0
100.96.0.0/16 dev flannel0  proto kernel  scope link  src 100.96.1.0
100.96.1.0/24 dev docker0  proto kernel  scope link  src 100.96.1.1
10.168.0.0/24 dev eth0  proto kernel  scope link  src 10.168.0.2
```

IP 包的目的地址是 100.96.2.3，它匹配不到本机 docker0 网桥对应的 100.96.1.0/24 网段，只能匹配到第二条、也就是 100.96.0.0/16 对应的这条路由规则，从而进入到一个叫作 flannel0 的设备中

flannel0是一个 TUN 设备（Tunnel 设备）

TUN 设备是一种工作在三层（Network Layer）的虚拟网络设备。TUN 设备的功能非常简单，即：在操作系统内核和用户应用程序之间传递 IP 包

当操作系统将一个 IP 包发送给 flannel0 设备之后，flannel0 就会把这个 IP 包，交给创建这个设备的应用程序，也就是 Flannel 进程。这是一个从内核态（Linux 操作系统）向用户态（Flannel 进程）的流动方向

反之，如果 Flannel 进程向 flannel0 设备发送了一个 IP 包，那么这个 IP 包就会出现在宿主机网络栈中，然后根据宿主机的路由表进行下一步处理。这是一个从用户态向内核态的流动方向。

当 IP 包从容器经过 docker0 出现在宿主机，然后又根据路由表进入 flannel0 设备后，宿主机上的 flanneld 进程（Flannel 项目在每个宿主机上的主进程），就会收到这个 IP 包。然后，flanneld 看到了这个 IP 包的目的地址，是 100.96.2.3，就把它发送给了 Node 2 宿主机

flanneld 又是如何知道这个 IP 地址对应的容器，是运行在 Node 2

在由 Flannel 管理的容器网络里，一台宿主机上的所有容器，都属于该宿主机被分配的一个“子网”

flanneld 进程在处理由 flannel0 传入的 IP 包时，就可以根据目的 IP 的地址（比如 100.96.2.3），匹配到对应的子网（比如 100.96.2.0/24），从 Etcd 中找到这个子网对应的宿主机的 IP 地址是 10.168.0.3

flanneld 在收到 container-1 发给 container-2 的 IP 包之后，就会把这个 IP 包直接封装在一个 UDP 包里，然后发送给 Node 2。不难理解，这个 UDP 包的源地址，就是 flanneld 所在的 Node 1 的地址，而目的地址，则是 container-2 所在的宿主机 Node 2 的地址。

这个请求得以完成的原因是，每台宿主机上的 flanneld，都监听着一个 8285 端口，所以 flanneld 只要把 UDP 包发往 Node 2 的 8285 端口即可

![image-20200511110556405](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511110556405.png)

![image-20200511111625291](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511111625291.png)

第一次，用户态的容器进程发出的 IP 包经过 docker0 网桥进入内核态；

第二次，IP 包根据路由表进入 TUN（flannel0）设备，从而回到用户态的 flanneld 进程；

第三次，flanneld 进行 UDP 封包之后重新进入内核态，将 UDP 包通过宿主机的 eth0 发出去。

##### VXLAN

**VXLAN，即 Virtual Extensible LAN（虚拟可扩展局域网），是 Linux 内核本身就支持的一种网络虚似化技术。所以说，VXLAN 可以完全在内核态实现上述封装和解封装的工作，从而通过与前面相似的“隧道”机制，构建出覆盖网络（Overlay Network）**

VXLAN 的覆盖网络的设计思想是：在现有的三层网络之上，“覆盖”一层虚拟的、由内核 VXLAN 模块负责维护的二层网络，使得连接在这个 VXLAN 二层网络上的“主机”（虚拟机或者容器都可以）之间，可以像在同一个局域网（LAN）里那样自由通信。当然，实际上，这些“主机”可能分布在不同的宿主机上，甚至是分布在不同的物理机房里

而为了能够在二层网络上打通“隧道”，VXLAN 会在宿主机上设置一个特殊的网络设备作为“隧道”的两端。这个设备就叫作 VTEP，即：VXLAN Tunnel End Point（虚拟隧道端点）。而 VTEP 设备的作用，其实跟前面的 flanneld 进程非常相似。只不过，**它进行封装和解封装的对象，是二层数据帧（Ethernet frame）；而且这个工作的执行流程，全部是在内核里完成的（因为 VXLAN 本身就是 Linux 内核中的一个模块）**

![image-20200511113200462](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511113200462.png)

与前面 UDP 模式的流程类似，当 container-1 发出请求之后，这个目的地址是 10.1.16.3 的 IP 包，会先出现在 docker0 网桥，然后被路由到本机 flannel.1 设备进行处理。也就是说，来到了“隧道”的入口

**为了能够将“原始 IP 包”封装并且发送到正确的宿主机，VXLAN 就需要找到这条“隧道”的出口，即：目的宿主机的 VTEP 设备。而这个设备的信息，正是每台宿主机上的 flanneld 进程负责维护的**

比如，当 Node 2 启动并加入 Flannel 网络之后，在 Node 1（以及所有其他节点）上，flanneld 就会添加一条如下所示的路由规则：

```

$ route -n
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
...
10.1.16.0       10.1.16.0       255.255.255.0   UG    0      0        0 flannel.1
```

**这条规则的意思是：凡是发往 10.1.16.0/24 网段的 IP 包，都需要经过 flannel.1 设备发出，并且，它最后被发往的网关地址是：10.1.16.0。**

**而这些 VTEP 设备之间，就需要想办法组成一个虚拟的二层网络，即：通过二层数据帧进行通信**

**而这里要用到的 ARP 记录，也是 flanneld 进程在 Node 2 节点启动时，自动添加在 Node 1 上的。我们可以通过 ip 命令看到它**

```shell

# 在Node 1上
$ ip neigh show dev flannel.1
10.1.16.0 lladdr 5e:f8:4f:00:e3:37 PERMANENT
```

![image-20200511145340865](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511145340865.png)

flannel.1 设备实际上要扮演一个“网桥”的角色，在二层网络进行 UDP 包的转发。而在 Linux 内核里面，“网桥”设备进行转发的依据，来自于一个叫作 FDB（Forwarding Database）的转发数据库

UDP 包是一个四层数据包，所以 Linux 内核会在它前面加上一个 IP 头，即原理图中的 Outer IP Header，组成一个 IP 包。并且，在这个 IP 头里，会填上前面通过 FDB 查询出来的目的主机的 IP 地址，即 Node 2 的 IP 地址 10.168.0.3

Linux 内核会把“目的 VTEP 设备”的 MAC 地址，填写在图中的 Inner Ethernet Header 字段，得到一个二层数据帧

![image-20200511145422169](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200511145422169.png)

Node 2 的内核网络栈会发现这个数据帧里有 VXLAN Header，并且 VNI=1。所以 Linux 内核会对它进行拆包，拿到里面的内部数据帧，然后根据 VNI 的值，把它交给 Node 2 上的 flannel.1 设备。

而 flannel.1 设备则会进一步拆包，取出“原始 IP 包”。接下来就回到了我在上一篇文章中分享的单机容器网络的处理流程。最终，IP 包就进入到了 container-2 容器的 Network Namespace 里

**Docker Overlay是通过vxlan隧道实现跨主机通信的**

![image-20200624104339374](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200624104339374.png)

## 参考

https://coolshell.cn/articles/17010.html

https://time.geekbang.org/column/article/115582

https://time.geekbang.org/column/article/64948

https://mp.weixin.qq.com/s?__biz=MzU0NDEyODkzMQ==&mid=2247497799&idx=1&sn=4577d681c62757a4a4343367b9e1547d&chksm=fb02528bcc75db9d3d263c7b8d43914b1e85e0a7fd4a54f5010c95e49ca3e82cfdec603cc685#rd

http://c.biancheng.net/view/3185.html

https://www.cnblogs.com/sparkdev/p/9198109.html

https://qiankunli.github.io/2020/04/18/docker_intro.html