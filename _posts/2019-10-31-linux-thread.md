---
date: 2019-10-31
layout: default

title: linux线程同步

---





## linux线程同步

Pthread的同步机制有Mutex Lock、Spin Lock、Reader-Writter Lock、join、Condition Variables、semaphore、Barriers



互斥锁(mutex)

pthread_mutex_lock(&mutex);

条件变量

信号量



### 条件变量

##### 有了互斥变量pthread_mutext_t为什么还要引入条件变量pthread_cond_t呢

条件变量是线程的另外一种同步机制，这些同步对象为线程提供了会合的场所，理解起来就是两个（或者多个）线程需要碰头（或者说进行交互-一个线程给另外的一个或者多个线程发送消息），我们指定在条件变量这个地方发生，一个线程用于修改这个变量使其满足其它线程继续往下执行的条件，其它线程则接收条件已经发生改变的信号。

条件变量同锁一起使用使得线程可以以一种无竞争的方式等待任意条件的发生。所谓无竞争就是，条件改变这个信号会发送到所有等待这个信号的线程。而不是说一个线程接受到这个消息而其它线程就接收不到了。

条件变量一共也就pthread_cond_init、pthread_cond_destroy、pthread_cond_wait、pthread_cond_timedwait、pthread_cond_signal、pthread_cond_broadcast这么几个函数

```c++
推荐用法

class Condition4 : public ConditionBase
{
public:
    Condition4()
        : signal_(false)
    {
    }

    void wait()
    {
        pthread_mutex_lock(&mutex_);
        while (!signal_)
        {
            pthread_cond_wait(&cond_, &mutex_);
        }
        signal_ = false;
        pthread_mutex_unlock(&mutex_);
    }

    void wakeup()
    {
        pthread_mutex_lock(&mutex_);
        signal_ = true;
        pthread_cond_signal(&cond_);
        pthread_mutex_unlock(&mutex_);
    }

private:
    bool signal_;
};

POSIX规范为了简化实现，允许pthread_cond_signal在实现的时候可以唤醒不止一个线程

java的park，unpark就是采用这个线程同步方式

notify和notify_all在linux系统就调用pthread_cond_signal、pthread_cond_broadcast，wait调用pthread_cond_wait

void os::PlatformEvent::park() {       // AKA "down()"
  // Transitions for _event:
  //   -1 => -1 : illegal
  //    1 =>  0 : pass - return immediately
  //    0 => -1 : block; then set _event to 0 before returning

  // Invariant: Only the thread associated with the PlatformEvent
  // may call park().
  assert(_nParked == 0, "invariant");

  int v;

  // atomically decrement _event
  for (;;) {
    v = _event;
    if (Atomic::cmpxchg(v - 1, &_event, v) == v) break;
  }
  guarantee(v >= 0, "invariant");

  if (v == 0) { // Do this the hard way by blocking ...
    int status = pthread_mutex_lock(_mutex);
    assert_status(status == 0, status, "mutex_lock");
    guarantee(_nParked == 0, "invariant");
    ++_nParked;
    while (_event < 0) {
      // OS-level "spurious wakeups" are ignored
      status = pthread_cond_wait(_cond, _mutex);
      assert_status(status == 0, status, "cond_wait");
    }
    --_nParked;

    _event = 0;
    status = pthread_mutex_unlock(_mutex);
    assert_status(status == 0, status, "mutex_unlock");
    // Paranoia to ensure our locked and lock-free paths interact
    // correctly with each other.
    OrderAccess::fence();
  }
  guarantee(_event >= 0, "invariant");
}


void os::PlatformEvent::unpark() {
  // Transitions for _event:
  //    0 => 1 : just return
  //    1 => 1 : just return
  //   -1 => either 0 or 1; must signal target thread
  //         That is, we can safely transition _event from -1 to either
  //         0 or 1.
  // See also: "Semaphores in Plan 9" by Mullender & Cox
  //
  // Note: Forcing a transition from "-1" to "1" on an unpark() means
  // that it will take two back-to-back park() calls for the owning
  // thread to block. This has the benefit of forcing a spurious return
  // from the first park() call after an unpark() call which will help
  // shake out uses of park() and unpark() without checking state conditions
  // properly. This spurious return doesn't manifest itself in any user code
  // but only in the correctly written condition checking loops of ObjectMonitor,
  // Mutex/Monitor, Thread::muxAcquire and os::sleep

  if (Atomic::xchg(1, &_event) >= 0) return;

  int status = pthread_mutex_lock(_mutex);
  assert_status(status == 0, status, "mutex_lock");
  int anyWaiters = _nParked;
  assert(anyWaiters == 0 || anyWaiters == 1, "invariant");
  status = pthread_mutex_unlock(_mutex);
  assert_status(status == 0, status, "mutex_unlock");

  // Note that we signal() *after* dropping the lock for "immortal" Events.
  // This is safe and avoids a common class of futile wakeups.  In rare
  // circumstances this can cause a thread to return prematurely from
  // cond_{timed}wait() but the spurious wakeup is benign and the victim
  // will simply re-test the condition and re-park itself.
  // This provides particular benefit if the underlying platform does not
  // provide wait morphing.

  if (anyWaiters != 0) {
    status = pthread_cond_signal(_cond);
    assert_status(status == 0, status, "cond_signal");
  }
}

https://www.cnblogs.com/liyuan989/p/4240271.html

```



Linux下使用`pthread_cond_signal`的时候，会产生“惊群”问题的，但是Java中是不会存在这个“惊群”问题的，那么Java是如何处理的呢？



<p>Java在语言层面实现了自己的线程管理机制（阻塞、唤醒、排队等），每个Thread实例都有一个独立的<code>pthread_mutex</code>和<code>pthread_cond</code>（系统层面的/C语言层面），在Java语言层面上对单个线程进行独立唤醒操作。</p>

PlatformParker主要看三个成员变量，_cur_index, _mutex, _cond。其中mutex和cond就是很熟悉的glibc nptl包中符合posix标准的线程同步工具，一个互斥锁一个条件变量。再看thread和Parker的关系，在hotspot的Thread类的NameThread内部类中有一个 Parker成员变量。说明parker是每线程变量，在创建线程的时候就会生成一个parker实例。



```c++
void Parker::park(bool isAbsolute, jlong time) {
  
  //原子交换，如果_counter > 0,则将_counter置为0，直接返回，否则_counter为0
  if (Atomic::xchg(0, &_counter) > 0) return;
  //获取当前线程
  Thread* thread = Thread::current();
  assert(thread->is_Java_thread(), "Must be JavaThread");
  //下转型为java线程
  JavaThread *jt = (JavaThread *)thread;
 
 
  //如果当前线程设置了中断标志，调用park则直接返回，所以如果在park之前调用了
  //interrupt就会直接返回
  if (Thread::is_interrupted(thread, false)) {
    return;
  }
 
  // 高精度绝对时间变量
  timespec absTime;
  //如果time小于0，或者isAbsolute是true并且time等于0则直接返回
  if (time < 0 || (isAbsolute && time == 0) ) { // don't wait at all
    return;
  }
  //如果time大于0，则根据是否是高精度定时计算定时时间
  if (time > 0) {
    unpackTime(&absTime, isAbsolute, time);
  }
 
 
  //进入安全点避免死锁
  ThreadBlockInVM tbivm(jt);
 
 
  //如果当前线程设置了中断标志，或者获取mutex互斥锁失败则直接返回
  //由于Parker是每个线程都有的，所以_counter cond mutex都是每个线程都有的，
  //不是所有线程共享的所以加锁失败只有两种情况，第一unpark已经加锁这时只需要返回即可，
  //第二调用调用pthread_mutex_trylock出错。对于第一种情况就类似是unpark先调用的情况，所以
  //直接返回。
  if (Thread::is_interrupted(thread, false) || pthread_mutex_trylock(_mutex) != 0) {
    return;
  }
 
  int status ;
  //如果_counter大于0，说明unpark已经调用完成了将_counter置为了1，
  //现在只需将_counter置0，解锁，返回
  if (_counter > 0)  { // no wait needed
    _counter = 0;
    status = pthread_mutex_unlock(_mutex);
    assert (status == 0, "invariant");
    OrderAccess::fence();
    return;
  }
 
 
  OSThreadWaitState osts(thread->osthread(), false /* not Object.wait() */);
  jt->set_suspend_equivalent();
  // cleared by handle_special_suspend_equivalent_condition() or java_suspend_self()
 
  assert(_cur_index == -1, "invariant");
  //如果time等于0，说明是相对时间也就是isAbsolute是fasle(否则前面就直接返回了),则直接挂起
  if (time == 0) {
    _cur_index = REL_INDEX; // arbitrary choice when not timed
    status = pthread_cond_wait (&_cond[_cur_index], _mutex) ;
  } else { //如果time非0
    //判断isAbsolute是false还是true，false的话使用_cond[0]，否则用_cond[1]
    _cur_index = isAbsolute ? ABS_INDEX : REL_INDEX;
    //使用条件变量使得当前线程挂起。
    status = os::Linux::safe_cond_timedwait (&_cond[_cur_index], _mutex, &absTime) ;
    //如果挂起失败则销毁当前的条件变量重新初始化。
    if (status != 0 && WorkAroundNPTLTimedWaitHang) {
      pthread_cond_destroy (&_cond[_cur_index]) ;
      pthread_cond_init    (&_cond[_cur_index], isAbsolute ? NULL : os::Linux::condAttr());
    }
  }
 
  //如果pthread_cond_wait成功则以下代码都是线程被唤醒后执行的。
  _cur_index = -1;
  assert_status(status == 0 || status == EINTR ||
                status == ETIME || status == ETIMEDOUT,
                status, "cond_timedwait");
 
#ifdef ASSERT
  pthread_sigmask(SIG_SETMASK, &oldsigs, NULL);
#endif
  //将_counter变量重新置为1
  _counter = 0 ;
  //解锁
  status = pthread_mutex_unlock(_mutex) ;
  assert_status(status == 0, status, "invariant") ;
  // 使用内存屏障使_counter对其它线程可见
  OrderAccess::fence();
 
  // 如果在park线程挂起的时候调用了stop或者suspend则还需要将线程挂起不能返回
  if (jt->handle_special_suspend_equivalent_condition()) {
    jt->java_suspend_self();
  }

```



###java 线程

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/thread.png)
![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/thread2.png)

![image-20191031152908741](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191031152908741.png)

![image-20191031163550430](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191031163550430.png)

![image-20200321212659597](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200321212659597.png)

```java
  public enum State {
        /**
         * Thread state for a thread which has not yet started.
         */
        NEW,

        /**
         * Thread state for a runnable thread.  A thread in the runnable
         * state is executing in the Java virtual machine but it may
         * be waiting for other resources from the operating system
         * such as processor.
         */
        RUNNABLE,

        /**
         * Thread state for a thread blocked waiting for a monitor lock.
         * A thread in the blocked state is waiting for a monitor lock
         * to enter a synchronized block/method or
         * reenter a synchronized block/method after calling
         * {@link Object#wait() Object.wait}.
         */
        BLOCKED,

        /**
         * Thread state for a waiting thread.
         * A thread is in the waiting state due to calling one of the
         * following methods:
         * <ul>
         *   <li>{@link Object#wait() Object.wait} with no timeout</li>
         *   <li>{@link #join() Thread.join} with no timeout</li>
         *   <li>{@link LockSupport#park() LockSupport.park}</li>
         * </ul>
         *
         * <p>A thread in the waiting state is waiting for another thread to
         * perform a particular action.
         *
         * For example, a thread that has called <tt>Object.wait()</tt>
         * on an object is waiting for another thread to call
         * <tt>Object.notify()</tt> or <tt>Object.notifyAll()</tt> on
         * that object. A thread that has called <tt>Thread.join()</tt>
         * is waiting for a specified thread to terminate.
         */
        WAITING,

        /**
         * Thread state for a waiting thread with a specified waiting time.
         * A thread is in the timed waiting state due to calling one of
         * the following methods with a specified positive waiting time:
         * <ul>
         *   <li>{@link #sleep Thread.sleep}</li>
         *   <li>{@link Object#wait(long) Object.wait} with timeout</li>
         *   <li>{@link #join(long) Thread.join} with timeout</li>
         *   <li>{@link LockSupport#parkNanos LockSupport.parkNanos}</li>
         *   <li>{@link LockSupport#parkUntil LockSupport.parkUntil}</li>
         * </ul>
         */
        TIMED_WAITING,

        /**
         * Thread state for a terminated thread.
         * The thread has completed execution.
         */
        TERMINATED;
    }
```

##### BLOCKED

synchronized 

##### WAITING/TIMED_WAITING

```java
线程执行如下方法会进入WAITING状态：
public final void join() throws InterruptedException
public final void wait() throws InterruptedException
执行如下方法会进入TIMED_WAITING状态：

public final native void wait(long timeout) throws InterruptedException;
public static native void sleep(long millis) throws InterruptedException;
public final synchronized void join(long millis) throws InterruptedException
```



阻塞：当一个线程试图获取对象锁（非java.util.concurrent库中的锁，即synchronized），而该锁被其他线程持有，则该线程进入阻塞状态。它的特点是**使用简单，由JVM调度器来决定唤醒自己，而不需要由另一个线程来显式唤醒自己，不响应中断**。
等待：当一个线程等待另一个线程通知调度器一个条件时，该线程进入等待状态。它的特点是**需要等待另一个线程显式地唤醒自己，实现灵活，语义更丰富，可响应中断**。例如调用：Object.wait()、Thread.join()以及等待Lock或Condition。

　　需要强调的是虽然synchronized和JUC里的Lock都实现锁的功能，但线程进入的状态是不一样的。**synchronized会让线程进入阻塞态，而JUC里的Lock是用LockSupport.park()/unpark()来实现阻塞/唤醒的，会让线程进入等待态**。但话又说回来，虽然等锁时进入的状态不一样，但被唤醒后又都进入runnable态，从行为效果来看又是一样的。



##### synchronized

在使用synchronized关键字获取锁的过程中不响应中断请求，这是synchronized的局限性。如果这对程序是一个问题，应该使用显式锁，java中的Lock接口，它支持以响应中断的方式获取锁。对于Lock.lock()，可以改用Lock.lockInterruptibly()，可被中断的加锁操作，它可以抛出中断异常。等同于等待时间无限长的Lock.tryLock(long time, TimeUnit unit)。



##### io操作

如果线程在等待IO操作，尤其是网络IO，则会有一些特殊的处理，我们没有介绍过网络，这里只是简单介绍下。

1. 实现此InterruptibleChannel接口的通道是可中断的：如果某个线程在可中断通道上因调用某个阻塞的 I/O 操作（常见的操作一般有这些：serverSocketChannel. accept()、socketChannel.connect、socketChannel.open、socketChannel.read、socketChannel.write、fileChannel.read、fileChannel.write）而进入阻塞状态，而另一个线程又调用了该阻塞线程的 interrupt 方法，这将导致该通道被关闭，并且已阻塞线程接将会收到ClosedByInterruptException，并且设置已阻塞线程的中断状态。另外，如果已设置某个线程的中断状态并且它在通道上调用某个阻塞的 I/O 操作，则该通道将关闭并且该线程立即接收到 ClosedByInterruptException；并仍然设置其中断状态。
2. 如果线程阻塞于Selector调用，则线程的中断标志位会被设置，同时，阻塞的调用会立即返回。

我们重点介绍另一种情况，**InputStream的read调用**，该操作是不可中断的，如果流中没有数据，read会阻塞 (但线程状态依然是RUNNABLE)，且不响应interrupt()，**与synchronized类似，调用interrupt()只会设置线程的中断标志，而不会真正”中断”它**

### reference

https://zhuanlan.zhihu.com/p/27857336

https://blog.csdn.net/a7980718/article/details/83661613