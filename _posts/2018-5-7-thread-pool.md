---
date: 2018-5-7
layout: default
title: 线程池
---
# 线程池

两种方式实现线程池

1. 线程池里的线程，不断从任务队列里拿任务执行；r = workQueue.take();

2. 多一个任务分派线程，当发现有线程空闲时，就从任务缓存队列中取一个任务交给空闲线程执行







## java实现的线程
一个人任务过来的时候：
当线程数小于核心线程，创建线程并执行。

当线程数=核心线程，把任务放入任务队列。

当任务队列没有空闲位置（如果队列无穷大？），并且线程数小于最大线程数，创建非核心线程。



### 拒绝策略

```java
 public void execute(Runnable command) {
        if (command == null)
            throw new NullPointerException();
        /*
         * Proceed in 3 steps:
         *
         * 1. If fewer than corePoolSize threads are running, try to
         * start a new thread with the given command as its first
         * task.  The call to addWorker atomically checks runState and
         * workerCount, and so prevents false alarms that would add
         * threads when it shouldn't, by returning false.
         *
         * 2. If a task can be successfully queued, then we still need
         * to double-check whether we should have added a thread
         * (because existing ones died since last checking) or that
         * the pool shut down since entry into this method. So we
         * recheck state and if necessary roll back the enqueuing if
         * stopped, or start a new thread if there are none.
         *
         * 3. If we cannot queue task, then we try to add a new
         * thread.  If it fails, we know we are shut down or saturated
         * and so reject the task.
         */
        int c = ctl.get();
        if (workerCountOf(c) < corePoolSize) {
            if (addWorker(command, true))
                return;
            c = ctl.get();
        }
        if (isRunning(c) && workQueue.offer(command)) {
            int recheck = ctl.get();
            if (! isRunning(recheck) && remove(command))
                reject(command);
            else if (workerCountOf(recheck) == 0)
                addWorker(null, false);
        }
        else if (!addWorker(command, false))
            reject(command);
    }
```

1. 线程池此时不处于running状态，调用拒绝策略拒绝任务
2. 线程池创建新的Worker失败，调用拒绝策略拒绝任务



线程池的拒绝策略有如下四种：

AbortPolicy:丢弃任务并抛出RejectedExecutionException异常 (默认)

```java
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    throw new RejectedExecutionException("Task " + r.toString() +
                                         " rejected from " +
                                         e.toString());
}
```

DiscardPolicy：也是丢弃任务，但是不抛出异常

```java
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
}
```

DiscardOldestPolicy：丢弃队列最前面的任务，执行后面的任务

```java
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    if (!e.isShutdown()) {
        e.getQueue().poll();
        e.execute(r);
    }
}
```

CallerRunsPolicy：由调用线程处理该任务 

```java
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    if (!e.isShutdown()) {
        r.run();
    }
}
```



## 任务队列
## 线程列表

