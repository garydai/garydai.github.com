---
date: 2021-6-7
layout: default
title: guava-cache


---

# Guava-cache

- 核心功能：高性能线程安全的in-heap Map数据结构 （类似于ConcurrentHashMap）
- **支持key不存在时按照给定的CacheLoader的loader方法进行Loading，如果有多个线程同时get一个不存在的key，那么有一个线程负责load，其他线程wait结果**
- 支持entry的evitBySize，这是一个LRU cache的基本功能
- 支持对entry设置过期时间，按照最后访问/写入的时间来淘汰entry
- 支持传入entry删除事件监听器，当entry被删除或者淘汰时执行监听器逻辑
- 支持对entry进行定期reload，默认使用loader逻辑进行同步reload (建议override CacheLoader的reload方法实现异步reload)
- 支持用WeakReference封装key，当key在应用程序里没有别的引用时，jvm会gc回收key对象，LoadingCache也会得到通知从而进行清理
- 支持用WeakReference或者SoftReference封装value对象
- 支持缓存相关运行数据指标的统计

## LRU实现

在Guava Cache的LRU实现中，它的双向链表并不是全局的(即这个那个Guava Cache只有一个)。而是每个Segment(ConcurrentHashMap中的概念)中都有。其中一共涉及到三个Queue其中包括：AccessQueue和WriteQueue，以及RecentQueue。其中AccessQueue和WriteQueue就是双向链表；而RecentQueue才是真正的Queue，它就是CocurrentLinkedQueue。接下来我们将分析Guava Cache是如何通过这三个Queue来实现的LRU。

没加锁的情况下（读），访问元素，加入cocurrentLinkedQueue，然后在加锁情况下（修改），将cocurrentLinkedQueue的数据放入accessQueue

## 删除策略



## 参考

http://kapsterio.github.io/test/2019/03/04/guava-loading-cache.html

https://blog.csdn.net/hilaryfrank/article/details/105739723