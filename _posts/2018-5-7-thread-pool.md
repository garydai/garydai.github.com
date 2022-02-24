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



## runnable

线程的实例化参数是runnable实例，没有返回值，怎么令线程返回结果呢

继承runnable接口，当线程执行run的时候，调用继承类FutureTask的run方法，即cglib继承代理的思想，不过是手动代理，将结果保存到对象的成员变量中

将任务抽象成runnable和future，runnable执行命令，future获取结果

```java
public interface RunnableFuture<V> extends Runnable, Future<V> {
    /**
     * Sets this Future to the result of its computation
     * unless it has been cancelled.
     */
    void run();
}
```

```java
public class FutureTask<V> implements RunnableFuture<V> {
  /** The underlying callable; nulled out after running */
    private Callable<V> callable;
    /** The result to return or exception to throw from get() */
    private Object outcome; // non-volatile, protected by state reads/writes
  
    public void run() {
        if (state != NEW ||
            !UNSAFE.compareAndSwapObject(this, runnerOffset,
                                         null, Thread.currentThread()))
            return;
        try {
            Callable<V> c = callable;
            if (c != null && state == NEW) {
                V result;
                boolean ran;
                try {
                    result = c.call();
                    ran = true;
                } catch (Throwable ex) {
                    result = null;
                    ran = false;
                    setException(ex);
                }
                if (ran)
                    set(result);
            }
        } finally {
            // runner must be non-null until state is settled to
            // prevent concurrent calls to run()
            runner = null;
            // state must be re-read after nulling runner to prevent
            // leaked interrupts
            int s = state;
            if (s >= INTERRUPTING)
                handlePossibleCancellationInterrupt(s);
        }
    }
}
```

java.util.concurrent.AbstractExecutorService#submit(java.util.concurrent.Callable<T>)

```java
public <T> Future<T> submit(Callable<T> task) {
    if (task == null) throw new NullPointerException();
    RunnableFuture<T> ftask = newTaskFor(task);
    // 将FutureTask送入线程池
    execute(ftask);
    return ftask;
}
```

## 任务队列

## 线程列表

## forkjoin

```java
package com.niuh.forkjoin.recursivetask;

import java.util.concurrent.RecursiveTask;

/**
 * RecursiveTask 并行计算，同步有返回值
 * ForkJoin框架处理的任务基本都能使用递归处理，比如求斐波那契数列等，但递归算法的缺陷是：
 * 一只会只用单线程处理，
 * 二是递归次数过多时会导致堆栈溢出；
 * ForkJoin解决了这两个问题，使用多线程并发处理，充分利用计算资源来提高效率，同时避免堆栈溢出发生。
 * 当然像求斐波那契数列这种小问题直接使用线性算法搞定可能更简单，实际应用中完全没必要使用ForkJoin框架，
 * 所以ForkJoin是核弹，是用来对付大家伙的，比如超大数组排序。
 * 最佳应用场景：多核、多内存、可以分割计算再合并的计算密集型任务
 */
class LongSum extends RecursiveTask<Long> {
    //任务拆分的最小阀值
    static final int SEQUENTIAL_THRESHOLD = 1000;
    static final long NPS = (1000L * 1000 * 1000);
    static final boolean extraWork = true; // change to add more than just a sum


    int low;
    int high;
    int[] array;

    LongSum(int[] arr, int lo, int hi) {
        array = arr;
        low = lo;
        high = hi;
    }

    /**
     * fork()方法：将任务放入队列并安排异步执行，一个任务应该只调用一次fork()函数，除非已经执行完毕并重新初始化。
     * tryUnfork()方法：尝试把任务从队列中拿出单独处理，但不一定成功。
     * join()方法：等待计算完成并返回计算结果。
     * isCompletedAbnormally()方法：用于判断任务计算是否发生异常。
     */
    protected Long compute() {

        if (high - low <= SEQUENTIAL_THRESHOLD) {
            long sum = 0;
            for (int i = low; i < high; ++i) {
                sum += array[i];
            }
            return sum;

        } else {
            int mid = low + (high - low) / 2;
            LongSum left = new LongSum(array, low, mid);
            LongSum right = new LongSum(array, mid, high);
            left.fork();
            right.fork();
            long rightAns = right.join();
            long leftAns = left.join();
            return leftAns + rightAns;
        }
    }
}


```



```java
package com.niuh.forkjoin.recursivetask;

import com.niuh.forkjoin.utils.Utils;

import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.ForkJoinTask;

public class LongSumMain {
    //获取逻辑处理器数量
    static final int NCPU = Runtime.getRuntime().availableProcessors();
    /**
     * for time conversion
     */
    static final long NPS = (1000L * 1000 * 1000);

    static long calcSum;

    static final boolean reportSteals = true;

    public static void main(String[] args) throws Exception {
        int[] array = Utils.buildRandomIntArray(2000000);
        System.out.println("cpu-num:" + NCPU);
        //单线程下计算数组数据总和
        long start = System.currentTimeMillis();
        calcSum = seqSum(array);
        System.out.println("seq sum=" + calcSum);
        System.out.println("singgle thread sort:->" + (System.currentTimeMillis() - start));

        start = System.currentTimeMillis();
        //采用fork/join方式将数组求和任务进行拆分执行，最后合并结果
        LongSum ls = new LongSum(array, 0, array.length);
        ForkJoinPool fjp = new ForkJoinPool(NCPU); //使用的线程数
        ForkJoinTask<Long> task = fjp.submit(ls);

        System.out.println("forkjoin sum=" + task.get());
        System.out.println("singgle thread sort:->" + (System.currentTimeMillis() - start));
        if (task.isCompletedAbnormally()) {
            System.out.println(task.getException());
        }

        fjp.shutdown();

    }


    static long seqSum(int[] array) {
        long sum = 0;
        for (int i = 0; i < array.length; ++i) {
            sum += array[i];
        }
        return sum;
    }
}


```

ForkJoinPool 的每个工作线程都维护着一个工作队列（WorkQueue），这是一个**双端队列（Deque）**，里面存放的对象是任务（**ForkJoinTask**）。

每个工作线程在运行中产生新的任务（通常是因为调用了 fork()）时，会放入工作队列的队尾，并且工作线程在处理自己的工作队列时，使用的是 **LIFO** 方式，也就是说每次从队尾取出任务来执行。

每个工作线程在处理自己的工作队列同时，会尝试窃取一个任务（或是来自于刚刚提交到 pool 的任务，或是来自于其他工作线程的工作队列），窃取的任务位于其他线程的工作队列的队首，也就是说工作线程在窃取其他工作线程的任务时，使用的是 FIFO 方式。

在遇到 join() 时，如果需要 join 的任务尚未完成，则会先处理其他任务，并等待其完成。

在既没有自己的任务，也没有可以窃取的任务时，进入休眠。



## 参考

https://juejin.cn/post/6906424424967667725
