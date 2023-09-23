---
date: 2020-8-2
layout: default
title: RocksDB


---

# RocksDB

[RocksDB](https://github.com/facebook/rocksdb) 是由 Facebook 基于 LevelDB 开发的一款提供键值存储与读写功能的 LSM-tree 架构引擎。用户写入的键值对会先写入磁盘上的 WAL (Write Ahead Log)，然后再写入内存中的跳表（SkipList，这部分结构又被称作 MemTable）。LSM-tree 引擎由于将用户的随机修改（插入）转化为了对 WAL 文件的顺序写，因此具有比 B 树类存储引擎更高的写吞吐。

内存中的数据达到一定阈值后，会刷到磁盘上生成 SST 文件 (Sorted String Table)，SST 又分为多层（默认至多 6 层），每一层的数据达到一定阈值后会挑选一部分 SST 合并到下一层，每一层的数据是上一层的 10 倍（因此 90% 的数据存储在最后一层）。

Levledb是Google的两位Fellow （Jeaf Dean和Sanjay Ghemawat）设计和开发的嵌入式K-V系统，读写性能非常彪悍，官方网站报道其写性能40万/s，读性能达到6万/s，写操作要远快于读操作。Rocksdb是Facebook公司在Leveldb基础之上开发的一个嵌入式K-V系统，**在很多方面对Leveldb做了优化和增强**，更像是一个完整的产品，比如：

1）Leveldb是单线程合并文件，Rocksdb可以支持**多线程合并**文件，充分利用多核的特性，加快文件合并的速度，避免文件合并期间引起系统停顿；

LSM型的数据结构，最大的性能问题就出现在其合并的时间损耗上，在多CPU的环境下，多线程合并那是LevelDB所无法比拟的。不过据其官网上的介绍，似乎多线程合并还只是针对那些与下一层没有Key重叠的文件，只是简单的rename而已，至于在真正数据上的合并方面是否也有用到多线程，就只能看代码了。

RocksDB增加了合并时过滤器，对一些不再符合条件的K-V进行丢弃，如根据K-V的有效期进行过滤。

2）Leveldb只有一个Memtable，若Memtable满了还没有来得及持久化，则会减缓Put操作引起系统停顿；RocksDB支持**管道式的Memtable**，也就说允许根据需要**开辟多个Memtable**，以解决Put与Compact速度差异的性能瓶颈问题。

3）Leveldb只能获取单个K-V；Rocksdb支持**一次获取多个K-V**，还支持**Key范围查找**。

4）Levledb不支持备份；Rocksdb支持**全量和增量备份**。RocksDB允许将已删除的数据备份到指定的目录，供后续恢复。

5）压缩方面RocksDB可采用**多种压缩算法**，除了LevelDB用的snappy，还有zlib、bzip2。LevelDB里面按数据的压缩率（压缩后低于75%）判断是否对数据进行压缩存储，而RocksDB典型的做法是Level 0-2不压缩，最后一层使用zlib，而其它各层采用snappy。

6）RocksDB除了简单的Put、Delete操作，还提供了一个**Merge操作**，说是为了对多个Put操作进行合并，优化了modify的效率。站在引擎实现者的角度来看，相比其带来的价值，其实现的成本要昂贵很多。个人觉得有时过于追求完美不见得是好事，据笔者所测（包括测试自己编写的引擎），性能的瓶颈其实主要在合并上，多一次少一次Put对性能的影响并无大碍。

7）RocksDB提供一些方便的工具，这些工具包含解析sst文件中的K-V记录、解析MANIFEST文件的内容等。有了这些工具，就不用再像使用LevelDB那样，只能在程序中才能知道sst文件K-V的具体信息了。

8）其他优化：增加了column family，这样有利于多个不相关的数据集存储在同一个db中，因为不同column family的数据是存储在不同的sst和memtable中，所以一定程度上起到了隔离的作用。将flush和compaction分开不同的线程池，能有效的加快flush，防止stall拖延停顿。增加了对write ahead log(WAL)的特殊管理机制，这样就能方便管理WAL文件，因为WAL是binlog文件。

## lsm-tree

LSM-Tree 的全称是：The Log-Structured Merge-Tree，是一种非常复杂的复合数据结构，它包含了 WAL（Write Ahead Log）、跳表（SkipList）和一个分层的有序表（SSTable，Sorted String Table）

![image-20211022130053296](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20211022130053296.png)

***1) MemTable***

MemTable是在***内存\***中的数据结构，用于保存最近更新的数据，会按照Key有序地组织这些数据，LSM树对于具体如何组织有序地组织数据并没有明确的数据结构定义，例如Hbase使跳跃表来保证内存中key的有序。

因为数据暂时保存在内存中，内存并不是可靠存储，如果断电会丢失数据，因此通常会通过WAL(Write-ahead logging，预写式日志)的方式来保证数据的可靠性。

***2) Immutable MemTable***

当 MemTable达到一定大小后，会转化成Immutable MemTable。Immutable MemTable是将转MemTable变为SSTable的一种中间状态。写操作由新的MemTable处理，在转存过程中不阻塞数据更新操作。

***3) SSTable(Sorted String Table)***

***有序键值对\***集合，是LSM树组在***磁盘\***中的数据结构。为了加快SSTable的读取，可以通过建立key的索引以及布隆过滤器来加快key的查找。



![image-20211022131116317](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20211022131116317.png)



这里需要关注一个重点，LSM树(Log-Structured-Merge-Tree)正如它的名字一样，LSM树会将所有的数据插入、修改、删除等操作记录(注意是操作记录)保存在内存之中，当此类操作达到一定的数据量后，再批量地顺序写入到磁盘当中。这与B+树不同，B+树数据的更新会直接在原数据所在处修改对应的值，但是LSM数的数据更新是日志式的，当一条数据更新是直接append一条更新记录完成的。这样设计的目的就是为了顺序写，不断地将Immutable MemTable flush到持久化存储即可，而不用去修改之前的SSTable中的key，保证了顺序写。

因此当MemTable达到一定大小flush到持久化存储变成SSTable后，在不同的SSTable中，可能存在相同Key的记录，当然最新的那条记录才是准确的。这样设计的虽然大大提高了写性能，但同时也会带来一些问题：

> 1）冗余存储，对于某个key，实际上除了最新的那条记录外，其他的记录都是冗余无用的，但是仍然占用了存储空间。因此需要进行Compact操作(合并多个SSTable)来清除冗余的记录。
> 2）读取时需要从最新的倒着查询，直到找到某个key的记录。最坏情况需要查询完所有的SSTable，这里可以通过前面提到的索引/布隆过滤器来优化查找速度。

## LSM树的Compact策略

从上面可以看出，Compact操作是十分关键的操作，否则SSTable数量会不断膨胀。在Compact策略上，主要介绍两种基本策略：size-tiered和leveled。

不过在介绍这两种策略之前，先介绍三个比较重要的概念，事实上不同的策略就是围绕这三个概念之间做出权衡和取舍。

> 1）读放大:读取数据时实际读取的数据量大于真正的数据量。例如在LSM树中需要先在MemTable查看当前key是否存在，不存在继续从SSTable中寻找。
> 2）写放大:写入数据时实际写入的数据量大于真正的数据量。例如在LSM树中写入时可能触发Compact操作，导致实际写入的数据量远大于该key的数据量。
> 3）空间放大:数据实际占用的磁盘空间比数据的真正大小更多。上面提到的冗余存储，对于一个key来说，只有最新的那条记录是有效的，而之前的记录都是可以被清理回收的。

见https://zhuanlan.zhihu.com/p/181498475

## 删除数据

我们已经解释了读取数据和写入数据的过程，那么删除数据又是如何处理的呢？我们已经知道 SSTable 是不可变的，所以里面的数据当然也不能够删除。其实删除操作其实和写入数据的操作是一样的，当需要删除数据的时候，我们把一个特定的标记（我们称之为 *墓碑(tombstone)* ）写入到这个key对应的位置，以标记为删除。

![image-20211022134147226](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20211022134147226.png)

上图演示了原来 key 为 `dog` 的值为 `52`，而删除之后就会变成一个墓碑的标记。当我们搜索键 `dog`的时候，将会返回数据无法查询，这就意味着删除操作其实也是占用磁盘空间的，最后墓碑的值将会被压缩，最后将会从磁盘删除。

![image-20200802164041348](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200802164041348.png)

当 LSM-Tree 收到一个写请求，比如说：PUT foo bar，把 Key foo 的值设置为 bar。首先，这条操作命令会被写入到磁盘的 WAL 日志中（图中右侧的 Log），这是一个顺序写磁盘的操作，性能很好。这个日志的唯一作用就是用于故障恢复，一旦系统宕机，可以从日志中把内存中还没有来得及写入磁盘的数据恢复出来。

然后数据会被写入到内存中的 MemTable 中，**这个 MemTable 就是一个按照 Key 组织的跳表（SkipList），跳表和平衡树有着类似的查找性能，但实现起来更简单一些**。写 MemTable 是个内存操作，速度也非常快。数据写入到 MemTable 之后，就可以返回写入成功了。这里面有一点需要注意的是，LSM-Tree 在处理写入的过程中，直接就往 MemTable 里写，并不去查找这个 Key 是不是已经存在了。

这个内存中 MemTable 不能无限地往里写，一是内存的容量毕竟有限，另外，MemTable 太大了读写性能都会下降。所以，MemTable 有一个固定的上限大小，一般是 32M。MemTable 写满之后，就被转换成 Immutable MemTable，然后再创建一个空的 MemTable 继续写。这个 Immutable MemTable，也就是只读的 MemTable，它和 MemTable 的数据结构完全一样，唯一的区别就是不允许再写入了

**当一个 Memtable 写满了之后，就会变成 immutable 的 Memtable，RocksDB 在后台会通过一个 flush 线程将这个 Memtable flush 到磁盘，生成一个 Sorted String Table(SST) 文件，放在 Level 0 层。当 Level 0 层的 SST 文件个数超过阈值之后，就会通过 Compaction 策略将其放到 Level 1 层，以此类推。**

到这里，虽然数据已经保存到磁盘上了，但还没结束，因为这些 SSTable 文件，虽然每个文件中的 Key 是有序的，但是文件之间是完全无序的，还是没法查找。这里 SSTable 采用了一个很巧妙的分层合并机制来解决乱序的问题。

SSTable 被分为很多层，越往上层，文件越少，越往底层，文件越多。每一层的容量都有一个固定的上限，一般来说，下一层的容量是上一层的 10 倍。当某一层写满了，就会触发后台线程往下一层合并，数据合并到下一层之后，本层的 SSTable 文件就可以删除掉了。合并的过程也是排序的过程，除了 Level 0（第 0 层，也就是 MemTable 直接 dump 出来的磁盘文件所在的那一层。）以外，每一层内的文件都是有序的，文件内的 KV 也是有序的，这样就比较便于查找了。

然后我们再来说 LSM-Tree 如何查找数据。查找的过程也是分层查找，先去内存中的 MemTable 和 Immutable MemTable 中找，然后再按照顺序依次在磁盘的每一层 SSTable 文件中去找，只要找到了就直接返回。这样的查找方式其实是很低效的，有可能需要多次查找内存和多个文件才能找到一个 Key，但实际的效果也没那么差，因为这样一个分层的结构，它会天然形成一个非常有利于查找的情况：越是被经常读写的热数据，它在这个分层结构中就越靠上，对这样的 Key 查找就越快。

比如说，最经常读写的 Key 很大概率会在内存中，这样不用读写磁盘就完成了查找。即使内存中查不到，真正能穿透很多层 SStable 一直查到最底层的请求还是很少的。另外，在工程上还会对查找做很多的优化，比如说，在内存中缓存 SSTable 文件的 Key，用布隆过滤器避免无谓的查找等来加速查找过程。这样综合优化下来，可以获得相对还不错的查找性能。



## 参考

https://docs.pingcap.com/zh/tidb/stable/rocksdb-overview

https://blog.csdn.net/weixin_44607611/article/details/113742388

https://zhuanlan.zhihu.com/p/181498475

https://segmentfault.com/a/1190000039269078

https://www.cnblogs.com/orange-CC/p/13212042.html