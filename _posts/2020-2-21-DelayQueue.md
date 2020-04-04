---
date: 2020-2-21
layout: default
title: DelayQueue
---

# DelayQueue

采用Leader-Fowller模式

leader是等待队列头部元素的指定线程。Leader-Follower模式的这种变体用于最小化不必要的定时等待。

- 当一个线程称为leader时，其会定时等待下一个delay元素过期，但是其他线程会无限期等待。
- 当从take/poll返回之前，leader线程必须signal其他等待线程，除非在此期间有线程称为了新的leader。
- 每当队列头部元素被更早到期的元素替换时，leader被置为null，offer里面q.peek() == e时，会将leader=null，此时当然会signal，重新竞选leader。所以定时等待线程必须要处理失去leader时情况。



```java
  public E take() throws InterruptedException {
        final ReentrantLock lock = this.lock;
        lock.lockInterruptibly();
        try {
            for (;;) {
                E first = q.peek();
                if (first == null)
                    available.await();
                else {
                    long delay = first.getDelay(NANOSECONDS);
                    if (delay <= 0)
                        return q.poll();
                    first = null; // don't retain ref while waiting
                    if (leader != null)
                        available.await();
                    else {
                        Thread thisThread = Thread.currentThread();
                        leader = thisThread;
                        try {
                          	// 只有leader线程，等待延迟时间，其他线程一直等待
                            available.awaitNanos(delay);
                        } finally {
                            if (leader == thisThread)
                                leader = null;
                        }
                    }
                }
            }
        } finally {
            if (leader == null && q.peek() != null)
                available.signal();
            lock.unlock();
        }
    }
```

## Leader-Follower模式

1）线程有3种状态：领导leading，处理processing，追随following

2）假设共N个线程，其中只有1个leading线程（等待任务），x个processing线程（处理），余下有N-1-x个following线程（空闲）

3）有一把锁，谁抢到就是leading

4）事件/任务来到时，leading线程会对其进行处理，从而转化为processing状态，处理完成之后，又转变为following

5）丢失leading后，following会尝试抢锁，抢到则变为leading，否则保持following

6）following不干事，就是抢锁，力图成为leading



## 参考

https://www.jianshu.com/p/e100cc737660
