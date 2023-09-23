---
date: 2022-4-5
layout: default
title: CompletableFuture
---

# CompletableFuture

每个CompletableFuture的方法都会新建CompletableFuture对象，并将当前方法需要执行的任务封装成Completion对象，之后将Completion压入到上个方法中创建的CompletableFuture对象的栈中，这样每个CompletableFuture对象的栈都保存了下一个待执行的任务，通过栈将每个任务串在一起，形成一个链条。当执行完当前CompletableFuture对象的任务后，接着查看栈中是否有任务，如果有则直接执行，如果没有就退出。后一个CompletableFuture对象也是一样，首先检查前一个任务是否执行完成，如果没有则将任务压入前一个对象的栈中，之后退出，如果前一个任务执行完成，则执行当前任务，然后查看栈中的任务。

```java
public static <U> CompletableFuture<U> supplyAsync(Supplier<U> supplier) {
	//asyncPool是一个线程池，
	//它根据配置或者CPU的个数来决定是使用ForkJoinPool还是ThreadPerTaskExecutor作为线程池的实现
    return asyncSupplyStage(asyncPool, supplier);
}
static <U> CompletableFuture<U> asyncSupplyStage(Executor e,
                                                 Supplier<U> f) {
    if (f == null) throw new NullPointerException();
    //创建一个新的CompletableFuture对象，所以后面调用thenAccept()方法其实使用的是这个新建的对象
    CompletableFuture<U> d = new CompletableFuture<U>();
    //在线程池中执行AsyncSupply
    e.execute(new AsyncSupply<U>(d, f));
    return d;
}
```

new一个CompletableFuture返回，结果也赋值在这个CompletableFuture上，下一个任务也放在CompletableFuture里的栈上

```java
public void run() {
    CompletableFuture<T> d; Supplier<T> f;
    //dep是在asyncSupplyStage()方法中新建的那个CompletableFuture对象
    //fn是自定义的Supplier对象
    if ((d = dep) != null && (f = fn) != null) {
        dep = null; fn = null;
        //CompletableFuture的result属性表示Supplier对象的执行结果，
        //更准确的说，result属性是用来记录我们编写的lambda表达式的运算结果的
        if (d.result == null) {
            try {
            	//使用CAS将Supplier的执行结果放入到属性result中
                d.completeValue(f.get());
            } catch (Throwable ex) {
            	//如果抛出异常，将异常对象记录到属性result
                d.completeThrowable(ex);
            }
        }
        //下面详细介绍postComplete()方法
        d.postComplete();
    }
}
--------------------------------------------------------------------------
	//postComplete()方法的作用是检查是否有下一个任务需要执行，如果需要便会触发该任务的执行
	//每调用一个CompletableFuture实例方法，CompletableFuture都将该实例方法要执行的任务封装成一个Completion对象，
	//并将Completion对象压入到当前CompletableFuture对象的栈中（栈顶使用stack属性记录），
	//也就是将后一个CompletableFuture对象的任务压入到前一个对象的栈中，
	//每次执行完当前任务后，都会调用postComplete()方法检查栈顶是否有待执行任务
    final void postComplete() {
        CompletableFuture<?> f = this; Completion h;
        //循环检查栈顶是否有待执行任务
        while ((h = f.stack) != null ||
               (f != this && (h = (f = this).stack) != null)) {
            CompletableFuture<?> d; Completion t;
            //casStack()将栈顶切换为下一个次栈顶元素
            if (f.casStack(h, t = h.next)) {
                if (t != null) {
                    if (f != this) {
                    	//当后一个CompletableFuture对象的栈中的任务需要嵌入到当前栈中执行时，
                    	//postComplete()获取到这些任务并调用pushStack()放入自己的栈中，
                    	//然后在本方法里面执行这些任务
                        pushStack(h);
                        continue;
                    }
                    h.next = null;    // detach
                }
                //如果栈中有待执行任务，调用tryFire()方法执行该任务，
                //如果tryFire()的入参为NESTED（值为-1），且返回的不是null，
                //说明后一个CompletableFuture对象的栈中的任务需要嵌入执行
                f = (d = h.tryFire(NESTED)) == null ? this : d;
            }
        }
    }


```

```java
public CompletableFuture<Void> thenAccept(Consumer<? super T> action) {
    return uniAcceptStage(null, action);
}
private CompletableFuture<Void> uniAcceptStage(Executor e,
                                               Consumer<? super T> f) {
    if (f == null) throw new NullPointerException();
    //新建一个CompletableFuture对象d，本方法将该对象返回给调用方
    CompletableFuture<Void> d = new CompletableFuture<Void>();
    //uniAccept()检查前一个任务是否执行完成，如果执行成功了，那么执行Consumer对象
    //注意：入参this指的是supplyAsync()方法里面创建的CompletableFuture对象
    //这里逻辑比较绕，一定分清楚现在调用的thenAccept()方法是属于是supplyAsync()方法里面创建的CompletableFuture对象的
    if (e != null || !d.uniAccept(this, f, null)) {
        UniAccept<T> c = new UniAccept<T>(e, d, this, f);
        //将UniAccept对象压入到CompletableFuture对象的栈中
        //这个栈是supplyAsync()方法里面创建的CompletableFuture对象的
        //push()方法使用CAS将对象c压入到栈
        push(c);
        c.tryFire(SYNC);
    }
    return d;
}
final <S> boolean uniAccept(CompletableFuture<S> a,
                            Consumer<? super S> f, UniAccept<S> c) {
    Object r; Throwable x;
    //a.result表示上一个任务的执行结果，如果为null，表示任务还在执行中
    //上一个任务没有执行完，直接退出当前方法
    if (a == null || (r = a.result) == null || f == null)
        return false;
    //result = null表示当前任务还没执行
    //能够执行下面的逻辑，说明上一个任务执行完毕，可以执行当前任务了
    tryComplete: if (result == null) {
        if (r instanceof AltResult) {
            if ((x = ((AltResult)r).ex) != null) {
                completeThrowable(x, r);
                break tryComplete;
            }
            r = null;
        }
        try {
            if (c != null && !c.claim())
                return false;
            @SuppressWarnings("unchecked") S s = (S) r;
            //执行Consumer任务
            f.accept(s);
            //向result属性设置结果
            completeNull();
        } catch (Throwable ex) {
            completeThrowable(ex);
        }
    }
    return true;
}
```



```java
final CompletableFuture<Void> tryFire(int mode) {
    CompletableFuture<Void> d; CompletableFuture<T> a;
    //dep表示thenAccept()方法中新建的CompletableFuture对象d
    //src表示supplyAsync()方法中创建的CompletableFuture对象
    if ((d = dep) == null ||
    	//uniAccept()在上面已经介绍过了
    	//这里调用uniAccept()方法可以确保在多线程环境下，Consumer对象已经可以被执行
        !d.uniAccept(a = src, fn, mode > 0 ? null : this))
        return null;
    dep = null; src = null; fn = null;
    //postFire()做收尾工作，检查对象a和对象d的栈是否有待执行任务，如果有分别调用postComplete()方法，
    //在调用前还会检查mode的值，如果mode为NESTED（-1），则说明栈的任务由别的线程执行，不再执行
    return d.postFire(a, mode);
}
final CompletableFuture<T> postFire(CompletableFuture<?> a, int mode) {
    if (a != null && a.stack != null) {
        if (mode < 0 || a.result == null)
            a.cleanStack();//清理栈，将执行过的任务从栈中清除
        else
            a.postComplete();//执行栈的任务，就本小节的例子来看，a栈的任务都已经执行过了
    }
    if (result != null && stack != null) {
        if (mode < 0)
            return this;//直接返回当前CompletableFuture对象，该对象的栈任务由其他线程执行
        else
            postComplete();//执行栈任务
    }
    return null;
}
```

![image-20220406113716925](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20220406113716925.png)

## 参考

https://blog.csdn.net/weixin_38308374/article/details/114681284