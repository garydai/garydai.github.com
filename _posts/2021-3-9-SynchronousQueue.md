---
date: 2021-3-9
layout: default
title: SynchronousQueue




---

# SynchronousQueue

SynchronousQueue是一个双栈双队列算法，无空间的队列或栈，任何一个对SynchronousQueue写需要等到一个对SynchronousQueue的读操作，反之亦然。一个读操作需要等待一个写操作，相当于是交换通道，提供者和消费者是需要组队完成工作，缺少一个将会阻塞线程，知道等到配对为止。

SynchronousQueue是一个队列和栈算法实现，在SynchronousQueue中双队列FIFO提供公平模式，而双栈LIFO提供的则是非公平模式。

相同模式入队

![image-20210310091038342](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210310091038342.png)

不同模式出队

![image-20210310091112216](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210310091112216.png)

## QNode

代表队列中的节点元素，它内部包含以下字段信息：

1. 字段信息描述

| 字段   | 描述           | 类型    |
| ------ | -------------- | ------- |
| next   | 下一个节点     | QNode   |
| item   | 元素信息       | Object  |
| waiter | 当前等待的线程 | Thread  |
| isData | 是否是数据     | boolean |

1. 方法信息描述

| 方法        | 描述                                                         |
| ----------- | ------------------------------------------------------------ |
| casNext     | 替换当前节点的next节点                                       |
| casItem     | 替换当前节点的item数据                                       |
| tryCancel   | 取消当前操作，将当前item赋值为this(当前QNode节点)            |
| isCancelled | 如果item是this(当前QNode节点)的话就返回true，反之返回false   |
| isOffList   | 如果已知此节点离队列，判断next节点是不是为this，则返回true，因为由于* advanceHead操作而忘记了其下一个指针。 |

```java
if (h == t || t.isData == isData) { // 队列为空或者模式相同时进行if语句
    QNode tn = t.next;
    if (t != tail)                  // 判断t是否是队尾，不是则重新循环。
        continue;
    if (tn != null) {               // tn是队尾的下个节点，如果tn有内容则将队尾更换为tn，并且重新循环操作。
        advanceTail(t, tn);
        continue;
    }
    if (timed && nanos <= 0)        // 如果指定了timed并且延时时间用尽则直接返回空，这里操作主要是offer操作时，因为队列无存储空间的当offer时不允许插入。
        return null;
    if (s == null)                                    // 这里是新节点生成。
        s = new QNode(e, isData);
    if (!t.casNext(null, s))        // 将尾节点的next节点修改为当前节点。
        continue;

    advanceTail(t, s);              // 队尾移动
    Object x = awaitFulfill(s, e, timed, nanos);    //自旋并且设置线程。
    if (x == s) {                   // wait was cancelled
        clean(t, s);
        return null;
    }

    if (!s.isOffList()) {           // not already unlinked
        advanceHead(t, s);          // unlink if head
        if (x != null)              // and forget fields
            s.item = s;
        s.waiter = null;
    }
    return (x != null) ? (E)x : e;

}
```

进入到if语句中的判断是如果头结点和尾节点相等代表队列为空，并没有元素所有要进行插入队列的操作，或者是队尾的节点的isData标志和当前操作的节点的类型一样时，会进行入队操作，isData标识当前元素是否是数据，如果为true代表是数据，如果为false则代表不是数据，换句话说只有模式相同的时候才会往队列中存放，如果不是模式相同的时候则代表互补模式，就不走if语句了，而是走了else语句

```java
} else {                            // 互补模式
    QNode m = h.next;               // 获取头结点的下一个节点，进行互补操作。
    if (t != tail || m == null || h != head)
        continue;                   // 这里就是为了防止阅读不一致的问题

    Object x = m.item;
    if (isData == (x != null) ||    // 如果x=null说明已经被读取了。
        x == m ||                   // x节点和m节点相等说明被中断操作，被取消操作了。
        !m.casItem(x, e)) {         // 这里是将item值设置为null
        advanceHead(h, m);          // 移动头结点到头结点的下一个节点
        continue;
    }

    advanceHead(h, m);              // successfully fulfilled
    LockSupport.unpark(m.waiter);
    return (x != null) ? (E)x : e;
}
```



## 参考

https://blog.csdn.net/qq_38293564/article/details/80604194

https://segmentfault.com/a/1190000019153021