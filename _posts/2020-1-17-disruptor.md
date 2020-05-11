---
date: 2020-1-17
layout: default
title: Disruptor
---

# Disruptor

1. JUC中的有界队列ArrayBlockingQueue和LinkedBlockingQueue，都是基于**ReentrantLock**
2. 在高并发场景下，锁的效率并不高，Disruptor是一款**性能更高**的有界内存队列
3. Disruptor高性能的原因
   - 内存分配更合理，使用RingBuffer，数组元素在初始化时一次性全部创建
     - **提升缓存命中率**，对象循环利用，**避免频繁GC**
   - 能够**避免伪共享**，提升缓存利用率
   - 采用**无锁算法**，避免频繁加锁、解锁的性能消耗
   - 支持**批量消费**，消费者可以以无锁的方式消费多个消息

## 缓存行填充

![image-20200117150134095](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200117150134095.png)



![image-20200117150156328](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200117150156328.png)



缓存是由缓存行组成的，通常是64字节，并且它有效地引用主内存中的一块地址。一个Java的long类型是8字节，因此在一个缓存行中可以存8个long类型的变量



![image-20200117151403418](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200117151403418.png)



设想你的消费者更新了`head`的值。缓存中的值和内存中的值都被更新了，而其他所有存储`head`的缓存行都会都会失效，因为其它缓存中`head`不是最新值了。请记住我们必须以整个缓存行作为单位来处理，所以同一个缓存行的数据即使没有被修改，也要重新从内存中读取到缓存

Disruptor消除这个问题，至少对于缓存行大小是64字节或更少的处理器架构来说是这样的（译注：有可能处理器的缓存行是128字节，那么使用64字节填充还是会存在伪共享问题），通过增加**补全**来确保ring buffer的序列号不会和其他东西同时存在于一个缓存行中。

```java
public long p1, p2, p3, p4, p5, p6, p7; // cache line padding
private volatile long cursor = INITIAL_CURSOR_VALUE;
public long p8, p9, p10, p11, p12, p13, p14; // cache line padding

```

Sequencer 序号分发器

Sequence 序号；cursor当前生产的事件序号

SequenceBarrier 阻挡消费者取序号的栅栏



插入一个内存屏障，相当于告诉CPU和编译器先于这个命令的必须先执行，后于这个命令的必须后执行

内存屏障另一个作用是强制更新一次不同CPU的缓存

如果你的字段是volatile，Java内存模型将在写操作后插入一个写屏障指令，在读操作前插入一个读屏障指令

## 消费

![image-20200117161501202](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200117161501202.png)



消费者线程的个数取决于我们构造 Disruptor 时提供的 EventHandler 的个数

每个消费都有自己的消费序号，有点像kafka

## 生产者**ProducerBarriers**

写入 Ring Buffer 的过程涉及到两阶段提交 (two-phase commit)。首先，你的生产者需要申请 buffer 里的下一个节点。然后，当生产者向节点写完数据，它将会调用 ProducerBarrier 的 commit 方法

![image-20200117163101927](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200117163101927.png)





下一个生产序号是3，但生产者会等消费者2把3消费了，才能写入新的消息。（**ConsumerTrackingProducerBarrier** 对象拥有所有正在访问 Ring Buffer 的 **消费者** 列表）

```java
public long tryNext(int n) throws InsufficientCapacityException
{
    if (n < 1)
    {
        throw new IllegalArgumentException("n must be > 0");
    }

    if (!hasAvailableCapacity(n, true))
    {
        throw InsufficientCapacityException.INSTANCE;
    }

    long nextSequence = this.nextValue += n;

    return nextSequence;
}
```

```java
public void publish(final long sequence)
{
    setAvailable(sequence);
    // 生产事件后，唤起消费线程
    waitStrategy.signalAllWhenBlocking();
}
```

## 多生产者

多个生产者的情况下，会遇到“如何防止多个线程重复写同一个元素”的问题。Disruptor的解决方法是，每个线程获取不同的一段数组空间进行操作。这个通过CAS很容易达到。只需要在分配元素的时候，通过CAS判断一下这段空间是否已经分配出去即可。

但是会遇到一个新问题：如何防止读取的时候，读到还未写的元素。Disruptor在多个生产者的情况下，引入了一个与Ring Buffer大小相同的buffer：available Buffer。当某个位置写入成功的时候，便把availble Buffer相应的位置置位，标记为写入成功。读取的时候，会遍历available Buffer，来判断元素是否已经就绪。

### 消费者

生产者多线程写入的情况会复杂很多： 1. 申请读取到序号n； 2. 若writer cursor >= n，这时仍然无法确定连续可读的最大下标。从reader cursor开始读取available Buffer，一直查到第一个不可用的元素，然后返回最大连续可读元素的位置； 3. 消费者读取元素。

#### 两种消费

在Disruptor中，消费者是以EventProcessor的形式存在的。

1. 其中一类消费者是BatchEvenProcessor。每个BatchEvenProcessor有一个Sequence，来记录自己消费RingBuffer中消息的情况。所以，一个消息必然会被每一个BatchEvenProcessor消费。

2. 共享同一个Sequence的WorkProcessor可由一个WorkerPool管理，这时，共享的Sequence也由WorkerPool创建。



线程池的方式workpool，**com.lmax.disruptor.dsl.Disruptor#createWorkerPool**

com.lmax.disruptor.WorkProcessor#run

```java
public void run()
{
    if (!running.compareAndSet(false, true))
    {
        throw new IllegalStateException("Thread is already running");
    }
    sequenceBarrier.clearAlert();

    notifyStart();

    // 默认上次消费成功
    boolean processedSequence = true;
    long cachedAvailableSequence = Long.MIN_VALUE;
    long nextSequence = sequence.get();
    T event = null;
    while (true)
    {
        try
        {
            // if previous sequence was processed - fetch the next sequence and set
            // that we have successfully processed the previous sequence
            // typically, this will be true
            // this prevents the sequence getting too far forward if an exception
            // is thrown from the WorkHandler
            if (processedSequence)
            {
              	// 上次消费成功，这次开始消费
                processedSequence = false;
                do
                {
                    // 设置当前线程消费的下一个事件序号
                    nextSequence = workSequence.get() + 1L;
                    sequence.set(nextSequence - 1L);
                }
                while (!workSequence.compareAndSet(nextSequence - 1L, nextSequence));
            }

            if (cachedAvailableSequence >= nextSequence)
            {
              	// 上次循环中，很多事件被产生，这次直接消费事件，不需要waitFor申请
                event = ringBuffer.get(nextSequence);
                workHandler.onEvent(event);
              	// 消费成功
                processedSequence = true;
            }
            else
            {
              	// 取下一个事件消费，当生产者生存了很多事件，所以可能会出现返回大于下一个事件序号的序号，保存在cachedAvailableSequence
                cachedAvailableSequence = sequenceBarrier.waitFor(nextSequence);
            }
        }
        catch (final TimeoutException e)
        {
            notifyTimeout(sequence.get());
        }
        catch (final AlertException ex)
        {
            if (!running.get())
            {
                break;
            }
        }
        catch (final Throwable ex)
        {
            // handle, mark as processed, unless the exception handler threw an exception
            exceptionHandler.handleEventException(ex, nextSequence, event);
            processedSequence = true;
        }
    }

    notifyShutdown();

    running.set(false);
}
```





一个线程对应一个BatchEventProcessor（eventhandler）

**com.lmax.disruptor.dsl.Disruptor#handleEventsWith(com.lmax.disruptor.EventHandler<? super T>...)**

com.lmax.disruptor.BatchEventProcessor#processEvents

```java
private void processEvents()
{
    T event = null;
    long nextSequence = sequence.get() + 1L;

    while (true)
    {
        try
        {
            final long availableSequence = sequenceBarrier.waitFor(nextSequence);
            if (batchStartAware != null)
            {
                batchStartAware.onBatchStart(availableSequence - nextSequence + 1);
            }

            while (nextSequence <= availableSequence)
            {
                event = dataProvider.get(nextSequence);
                eventHandler.onEvent(event, nextSequence, nextSequence == availableSequence);
                nextSequence++;
            }

            sequence.set(availableSequence);
        }
        catch (final TimeoutException e)
        {
            notifyTimeout(sequence.get());
        }
        catch (final AlertException ex)
        {
            if (running.get() != RUNNING)
            {
                break;
            }
        }
        catch (final Throwable ex)
        {
            exceptionHandler.handleEventException(ex, nextSequence, event);
            sequence.set(nextSequence);
            nextSequence++;
        }
    }
}
```

com.lmax.disruptor.ProcessingSequenceBarrier#waitFor

```java
public long waitFor(final long sequence)
    throws AlertException, InterruptedException, TimeoutException
{
    checkAlert();

  	// 不同的等待策略
    long availableSequence = waitStrategy.waitFor(sequence, cursorSequence, dependentSequence, this);

    if (availableSequence < sequence)
    {
        return availableSequence;
    }

    return sequencer.getHighestPublishedSequence(sequence, availableSequence);
}
```

com.lmax.disruptor.BlockingWaitStrategy#waitFor

```java
public long waitFor(long sequence, Sequence cursorSequence, Sequence dependentSequence, SequenceBarrier barrier)
    throws AlertException, InterruptedException
{
    long availableSequence;
    if (cursorSequence.get() < sequence)
    {
        lock.lock();
        try
        {
            while (cursorSequence.get() < sequence)
            {
                barrier.checkAlert();
                processorNotifyCondition.await();
            }
        }
        finally
        {
            lock.unlock();
        }
    }

    while ((availableSequence = dependentSequence.get()) < sequence)
    {
        barrier.checkAlert();
        ThreadHints.onSpinWait();
    }

    return availableSequence;
}
```

com.lmax.disruptor.TimeoutBlockingWaitStrategy#waitFor

```java
public long waitFor(
    final long sequence,
    final Sequence cursorSequence,
    final Sequence dependentSequence,
    final SequenceBarrier barrier)
    throws AlertException, InterruptedException, TimeoutException
{
    long nanos = timeoutInNanos;

    long availableSequence;
    if (cursorSequence.get() < sequence)
    {
        lock.lock();
        try
        {
            while (cursorSequence.get() < sequence)
            {
                barrier.checkAlert();
                nanos = processorNotifyCondition.awaitNanos(nanos);
                if (nanos <= 0)
                {
                    throw TimeoutException.INSTANCE;
                }
            }
        }
        finally
        {
            lock.unlock();
        }
    }

    while ((availableSequence = dependentSequence.get()) < sequence)
    {
        barrier.checkAlert();
    }

    return availableSequence;
}
```

### 生产者

多个生产者写入的时候： 1. 申请写入m个元素； 2. 若是有m个元素可以写入，则返回最大的序列号。每个生产者会被分配一段独享的空间； 3. 生产者写入元素，写入元素的同时设置available Buffer里面相应的位置，以标记自己哪些位置是已经写入成功的。

![image-20200119134839727](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200119134839727.png)

分配m个元素之后，cas改变cursor，如果改变失败，spin死循环，直到成功。解决并发问题的常规操作

```java
public long tryNext(int n) throws InsufficientCapacityException
{
    if (n < 1)
    {
        throw new IllegalArgumentException("n must be > 0");
    }

    long current;
    long next;

    do
    {
        current = cursor.get();
        next = current + n;

        if (!hasAvailableCapacity(gatingSequences, n, current))
        {
            throw InsufficientCapacityException.INSTANCE;
        }
    }
  	// cas改变cursor值，解决并发问题的常规操作
    while (!cursor.compareAndSet(current, next));

    return next;
}
```

```java
private boolean hasAvailableCapacity(Sequence[] gatingSequences, final int requiredCapacity, long cursorValue)
{
    long wrapPoint = (cursorValue + requiredCapacity) - bufferSize;
    long cachedGatingSequence = gatingSequenceCache.get();

    if (wrapPoint > cachedGatingSequence || cachedGatingSequence > cursorValue)
    {
        long minSequence = Util.getMinimumSequence(gatingSequences, cursorValue);
        gatingSequenceCache.set(minSequence);

        if (wrapPoint > minSequence)
        {
            return false;
        }
    }

    return true;
}
```



http://ifeve.com/disruptor-cacheline-padding/

http://ifeve.com/dissecting-disruptor-whats-so-special/

https://tech.meituan.com/2016/11/18/disruptor.html

http://zhongmingmao.me/2019/05/31/java-concurrent-disruptor/