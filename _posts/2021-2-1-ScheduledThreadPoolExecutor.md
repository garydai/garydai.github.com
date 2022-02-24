---
date: 2021-2-1
layout: default
title: ScheduledThreadPoolExecutor

---

# ScheduledThreadPoolExecutor

PriorityQueue优先队列，最小堆

PriorityBlockingQueue，实现了BlockingQueue接口，使PriorityQueue线程安全同时通过take，put使线程间灵活的通信

DelayQueue，DelayQueue = PriorityBlockQueue + Delay，也就是说，PriorityQueue的优先级大小是由Delay来决定的

ScheduledThreadPoolExecutor里的DelayedWorkQueue有点类似DelayQueue

```java
/**
 * Thread designated to wait for the task at the head of the
 * queue.  This variant of the Leader-Follower pattern
 * (http://www.cs.wustl.edu/~schmidt/POSA/POSA2/) serves to
 * minimize unnecessary timed waiting.  When a thread becomes
 * the leader, it waits only for the next delay to elapse, but
 * other threads await indefinitely.  The leader thread must
 * signal some other thread before returning from take() or
 * poll(...), unless some other thread becomes leader in the
 * interim.  Whenever the head of the queue is replaced with a
 * task with an earlier expiration time, the leader field is
 * invalidated by being reset to null, and some waiting
 * thread, but not necessarily the current leader, is
 * signalled.  So waiting threads must be prepared to acquire
 * and lose leadership while waiting.
 */
private Thread leader = null;
```

定时任务放入延迟队列（最小堆）

**同一时间只有leader线程在等待一段超时时间，其他follower线程永久等待，然后leader执行任务，执行完成再唤醒其他followers**

java.util.concurrent.ScheduledThreadPoolExecutor.DelayedWorkQueue#take

```java
public RunnableScheduledFuture<?> take() throws InterruptedException {
    final ReentrantLock lock = this.lock;
    lock.lockInterruptibly();
    try {
        for (;;) {
            RunnableScheduledFuture<?> first = queue[0];
            if (first == null)
                available.await();
            else {
                long delay = first.getDelay(NANOSECONDS);
                if (delay <= 0)
                    return finishPoll(first);
                first = null; // don't retain ref while waiting
                // 只有leader线程等待超时时间，其他线程永久等待
                if (leader != null)
                    available.await();
                else {
                    Thread thisThread = Thread.currentThread();
                    leader = thisThread;
                    try {
                        available.awaitNanos(delay);
                    } finally {
                        if (leader == thisThread)
                            leader = null;
                    }
                }
            }
        }
    } finally {
        if (leader == null && queue[0] != null)
            available.signal();
        lock.unlock();
    }
}
```

```java
public boolean offer(Runnable x) {
    if (x == null)
        throw new NullPointerException();
    RunnableScheduledFuture<?> e = (RunnableScheduledFuture<?>)x;
    final ReentrantLock lock = this.lock;
    lock.lock();
    try {
        int i = size;
        if (i >= queue.length)
            grow();
        size = i + 1;
        if (i == 0) {
            queue[0] = e;
            setIndex(e, 0);
        } else {
            siftUp(i, e);
        }
        if (queue[0] == e) {
           // 如果更早的任务来临，设置leader=null，其他线程能成为leader执行这个最早的任务
            leader = null;
            available.signal();
        }
    } finally {
        lock.unlock();
    }
    return true;
}
```

## leader-follower模型

在Java开源框架中很少看到这种线程模式的使用，但是在JUC包DelayQueue的实现中却有着Leader-Follower线程模型的思想存在。

![image-20210201114636208](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210201114636208.png)



所有线程会有三种身份中的一种：leader和follower，以及一个干活中的状态：proccesser。它的基本原则就是，永远最多只有一个leader。而所有follower都在等待成为leader。线程池启动时会自动产生一个Leader负责等待网络IO事件，当有一个事件产生时，Leader线程首先通知一个Follower线程将其提拔为新的Leader，然后自己就去干活了，去处理这个网络事件，处理完毕后加入Follower线程等待队列，等待下次成为Leader。这种方法可以增强CPU高速缓存相似性，及消除动态内存分配和线程间的数据交换。

![image-20210201120821618](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210201120821618.png)



## 参考

https://blog.csdn.net/goldlevi/article/details/7705180

http://www.ligen.pro/2018/01/15/PriorityQueue及其相关衍生队列源码分析/









一个生产者多个消费者，futureTask，一个锁、voliatile、park、unpark

一个生产者一个消费者

多个生产者一个消费者 mpsc，队列，notEmpty与notFull

多个生产者多个消费者 mpmc，队列，notEmpty与notFull



单一锁

锁分离

读写锁

乐观锁



