---
date: 2020-6-11
layout: default
title: weakReference
---

# weakReference

```java
public abstract class Reference<T> {
    //引用的对象
    private T referent;        
	//回收队列，由使用者在Reference的构造函数中指定
    volatile ReferenceQueue<? super T> queue;
 	//当该引用被加入到queue中的时候，该字段被设置为queue中的下一个元素，以形成链表结构
    volatile Reference next;
    //在GC时，JVM底层会维护一个叫DiscoveredList的链表，存放的是Reference对象，discovered字段指向的就是链表中的下一个元素，由JVM设置
    transient private Reference<T> discovered;  
	//进行线程同步的锁对象
    static private class Lock { }
    private static Lock lock = new Lock();
	//等待加入queue的Reference对象，在GC时由JVM设置，会有一个java层的线程(ReferenceHandler)源源不断的从pending中提取元素加入到queue
    private static Reference<Object> pending = null;
}
```

一个Reference对象的生命周期如下

![image-20200611142246450](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200611142246450.png)



## 我们来看Young GC的时候，到底发生了什么？

### Native层

Native层在GC时将需要被回收的Reference对象加入到DiscoveredList中（代码在`referenceProcessor.cpp`中`process_discovered_references`方法），然后将DiscoveredList的元素移动到PendingList中（代码在`referenceProcessor.cpp`中`enqueue_discovered_ref_helper`方法）,PendingList的队首就是Reference类中的pending对象

### java层

```java
private static class ReferenceHandler extends Thread {
     	...
        public void run() {
            while (true) {
                tryHandlePending(true);
            }
        }
  } 
static boolean tryHandlePending(boolean waitForNotify) {
        Reference<Object> r;
        Cleaner c;
        try {
            synchronized (lock) {
                if (pending != null) {
                    r = pending;
                 	//如果是Cleaner对象，则记录下来，下面做特殊处理
                    c = r instanceof Cleaner ? (Cleaner) r : null;
                    //指向PendingList的下一个对象
                    pending = r.discovered;
                    r.discovered = null;
                } else {
                   //如果pending为null就先等待，当有对象加入到PendingList中时，jvm会执行notify
                    if (waitForNotify) {
                        lock.wait();
                    }
                    // retry if waited
                    return waitForNotify;
                }
            }
        } 
        ...

        // 如果时CLeaner对象，则调用clean方法进行资源回收
        if (c != null) {
            c.clean();
            return true;
        }
		//将Reference加入到ReferenceQueue，开发者可以通过从ReferenceQueue中poll元素感知到对象被回收的事件。
        ReferenceQueue<? super Object> q = r.queue;
        if (q != ReferenceQueue.NULL) q.enqueue(r);
        return true;
 }
```


Java层流程比较简单：就是源源不断的从PendingList中提取出元素，然后将其加入到ReferenceQueue中去，开发者可以通过从ReferenceQueue中poll元素感知到对象被回收的事件。

对于Cleaner类型（继承自虚引用）的对象会有额外的处理：在其指向的对象被回收时，会调用clean方法，该方法主要是用来做对应的资源回收，**在堆外内存DirectByteBuffer中就是用Cleaner进行堆外内存的回收，这也是虚引用在java中的典型应用**



**总流程**
reference-JVM->pending-JAVA->referenceQueue





## WeakHashMap

WeakHashMap的expungeStaleEntries方法，将value也置为null

```csharp
此方法会在3个地方进行调用
getTable()，这个getTable基本上会在所有的get，put等方法中进行调用
resize()
size()
```

这个方法就是删除陈旧的数据。

前面ReferenceQueue中提到了，对象不可达时，poll方法会返回null，但这返回null只是返回，真正目前虚拟机中，只有key为显式置为null了，后面还要把value显示置为null

```java
    /**
     * Expunges stale entries from the table.
     */
    private void expungeStaleEntries() {
        for (Object x; (x = queue.poll()) != null; ) {
            synchronized (queue) {
                @SuppressWarnings("unchecked")
                    Entry<K,V> e = (Entry<K,V>) x;
                int i = indexFor(e.hash, table.length);

                Entry<K,V> prev = table[i];
                Entry<K,V> p = prev;
                while (p != null) {
                    Entry<K,V> next = p.next;
                    if (p == e) {
                        if (prev == e)
                            table[i] = next;
                        else
                            prev.next = next;
                        // Must not null out e.next;
                        // stale entries may be in use by a HashIterator
                        e.value = null; // Help GC
                        size--;
                        break;
                    }
                    prev = p;
                    p = next;
                }
            }
        }
    }
```



## 参考

https://www.jianshu.com/p/12ed2f0a250c

https://github.com/farmerjohngit/myblog/issues/10