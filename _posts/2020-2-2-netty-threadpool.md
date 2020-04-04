---
date: 2020-2-2
layout: default
title: netty-threadpool
---

# netty-threadpool

jdk实现线程池是用ThreadPoolExecutor继承AbstractExecutorService，方式是**任务放入一个队列，然后开启多个线程**

netty没有使用jdk的threadPoolExecutor，而是自己实现，也是通过继承jdk的AbstractExecutorService

jdk抽象类

```java
public abstract class AbstractEventExecutor extends AbstractExecutorService implements EventExecutor
```



netty继承jdk抽象类

```java
public abstract class AbstractScheduledEventExecutor extends AbstractEventExecutor
```



单线程线程池

```java
public abstract class SingleThreadEventExecutor extends AbstractScheduledEventExecutor implements OrderedEventExecutor
{
  队列使用 LinkedBlockingQueue
}
```



多线程线程池

```java
public interface EventExecutorGroup extends ScheduledExecutorService, Iterable<EventExecutor> 
```

```java
public interface EventLoopGroup extends EventExecutorGroup
```

```java
public abstract class AbstractEventExecutorGroup implements EventExecutorGroup
{
  next().xxx
}
```

```java
public abstract class MultithreadEventExecutorGroup extends AbstractEventExecutorGroup
{
  private final EventExecutor[] children;
  实现了next()，以一定策略EventExecutorChooserFactory.EventExecutorChooser，选择children里的EventExecutor
}
```

```java
public abstract class MultithreadEventLoopGroup extends MultithreadEventExecutorGroup implements EventLoopGroup
```

NioEventLoopGroup线程池实现方式是，生成多个children，每个child是单线程线程池SingleThreadEventExecutor，所以是**一个线程对应一个队列，有多组**

```java
public class NioEventLoopGroup extends MultithreadEventLoopGroup {
  
      protected EventLoop newChild(Executor executor, Object... args) throws Exception {
        EventLoopTaskQueueFactory queueFactory = args.length == 4 ? (EventLoopTaskQueueFactory) args[3] : null;
        // NioEventLoop是个单线程线程池SingleThreadEventExecutor
        return new NioEventLoop(this, executor, (SelectorProvider) args[0],
            ((SelectStrategyFactory) args[1]).newSelectStrategy(), (RejectedExecutionHandler) args[2], queueFactory);
    }
}
```

```java
public final class NioEventLoop extends SingleThreadEventLoop {
  重写newTaskQueue，使用Mpsc.newMpscQueue（org.jctools.queues的多生产者单生成者队列）
}
```

```java
public abstract class SingleThreadEventLoop extends SingleThreadEventExecutor implements EventLoop
```