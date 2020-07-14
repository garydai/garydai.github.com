---
date: 2019-11-22
layout: default
title: java 引用
---

# java 引用

## 强引用StrongReference

垃圾回收的时候，即使内存不足也不会回收

```java
Object obj = new Object();
```

## 软引用SoftReferenc

```java
package javalearning;
 
import java.lang.ref.SoftReference;
/*
 * 虚拟机参数配置
 * -Xms256m
 * -Xmx1024m
*/
public class SoftReferenceDemo {
    public static void main(String[] args){
         
        /*软引用对象中指向了一个长度为300000000个元素的整形数组*/
        SoftReference<int[]> softReference = 
                new SoftReference<int[]>(new int[300000000]);
         
        /*主动调用一次gc,由于此时JVM的内存够用，此时softReference引用的对象未被回收*/
        System.gc();
        System.out.println(softReference.get());
         
        /*消耗内存,会导致一次自动的gc,此时JVM的内存不够用
         *就回收softReference对象中指向的数组对象*/
        int[] strongReference = new int[100000000];
         
        System.out.println(softReference.get());
    }
}
```

如果内存空间足够，垃圾回收器就不会回收它，如果内存空间不足了，就会回收这些对象的内存

软引用可用来实现内存敏感的高速缓存

```java
MyObject aRef = new MyObject();
SoftReference aSoftRef=new SoftReference(aRef);
aRef = null;
//现在只有一个软引用指向MyObject的这个对象，
//如果这个对象还没有被回收，可以把他再次变为强引用
if(aSoftRef.get() != null)
  MyObject bRef = aSoftRef.get();
//这个时候MyObject这个对象又变成强引用
```

除了幻象引用（因为 get 永远返回 null），如果对象还没有被销毁，都可以通过 get 方法获取原有对象。这意味着，利用软引用和弱引用，我们可以将访问到的对象，重新指向强引用

所以，对于软引用、弱引用之类，垃圾收集器可能会存在二次确认的问题，以保证处于弱引用状态的对象，没有改变为强引用。

```java
public class SoftReference<T> extends Reference<T> {
    
    static private long clock;
    
    private long timestamp;
   
    public SoftReference(T referent) {
        super(referent);
        this.timestamp = clock;
    }
 
    public SoftReference(T referent, ReferenceQueue<? super T> q) {
        super(referent, q);
        this.timestamp = clock;
    }

    public T get() {
        T o = super.get();
        if (o != null && this.timestamp != clock)
            this.timestamp = clock;
        return o;
    }

}
```

`clock`和`timestamp`。`clock`是个静态变量，每次GC时都会将该字段设置成当前时间。`timestamp`字段则会在每次调用get方法时将其赋值为`clock`（如果不相等且对象没被回收）。

## 弱引用WeakReferenc

当JVM进行垃圾回收时，无论内存是否充足，都会回收仅被弱引用关联的对象

```java
package javalearning;
 
import java.lang.ref.WeakReference;
 
public class WeakReferenceDemo {
    public static void main(String[] args){
 
        /*若引用对象中指向了一个长度为1000个元素的整形数组*/
        WeakReference<String[]> weakReference = 
                new WeakReference<String[]>(new String[1000]);
         
        /*未执行gc,目前仅被弱引用指向的对象还未被回收，所以结果不是null*/     
        System.out.println(weakReference.get());
         
        /*执行一次gc,即使目前JVM的内存够用,但还是回收仅被弱引用指向的对象*/
        System.gc();
        System.out.println(weakReference.get());
    }
}
```



## 幻象引用PhantomReference

如果一个对象仅持有虚引用，那么它就和没有任何引用一样，在任何时候都可能被垃圾回收

```java
public static void demo() throws InterruptedException {
        Object obj = new Object();
        ReferenceQueue<Object> refQueue =new ReferenceQueue<>();
        PhantomReference<Object> phanRef =new PhantomReference<>(obj, refQueue);

        Object objg = phanRef.get();
        //这里拿到的是null
        System.out.println(objg);
        //让obj变成垃圾
        obj=null;
        System.gc();
        Thread.sleep(3000);
		//gc后会将phanRef加入到refQueue中
        Reference<? extends Object> phanRefP = refQueue.remove();
     	//这里输出true
        System.out.println(phanRefP==phanRef);
    }
```

对于Soft references和Weak references `clear_referent`字段传入的都是true，这也符合我们的预期：对象不可达后，引用字段就会被置为null，然后对象就会被回收（对于软引用来说，如果内存足够的话，在Phase 1，相关的引用就会从refs_list中被移除，到Phase 3时refs_list为空集合）。

但对于Final references和 Phantom references，`clear_referent`字段传入的是false，也就意味着被这两种引用类型引用的对象，**如果没有其他额外处理，只要Reference对象还存活，那引用的对象是不会被回收的**。Final references和对象是否重写了finalize方法有关，不在本文分析范围之内，我们接下来看看Phantom references。



虚引用能够在指向对象不可达时得到一个'通知'（其实所有继承References的类都有这个功能），需要注意的是GC完成后，**phanRef.referent依然指向之前创建Object，也就是说Object对象一直没被回收！**

而造成这一现象的原因在上一小节末尾已经说了：`对于Final references和 Phantom references，`clear_referent`字段传入的时false，也就意味着被这两种引用类型引用的对象，如果没有其他额外处理，在GC中是不会被回收的。`

对于虚引用来说，从`refQueue.remove();`得到引用对象后，可以调用`clear`方法强行解除引用和对象之间的关系，使得对象下次可以GC时可以被回收掉。

## 引用队列

当gc（垃圾回收线程）准备回收一个对象时，如果发现它还仅有软引用(或弱引用，或虚引用)指向它，就会在回收该对象之前，把这个软引用（或弱引用，或虚引用）加入到与之关联的引用队列

如果一个软引用（或弱引用，或虚引用）**对象本身**在引用队列中，就说明该引用对象所**指向的对象**被回收了

当软引用（或弱引用，或虚引用）对象所指向的对象被回收了，那么这个引用对象本身就没有价值了，如果程序中存在大量的这类对象（注意，我们创建的软引用、弱引用、虚引用对象本身是个强引用，不会自动被gc回收），就会浪费内存。因此我们这就可以手动回收位于引用队列中的引用对象本身

```java
package javalearning;
 
import java.lang.ref.ReferenceQueue;
import java.lang.ref.SoftReference;
 
public class ReferenceQueneDemo {
     
    @SuppressWarnings({ "rawtypes", "unchecked" })
    public static void main(String[] args){
        /*创建引用队列*/
        ReferenceQueue<SoftReference<int[]>> rq = 
                new ReferenceQueue<SoftReference<int[]>>();
         
        /*创建一个软引用数组，每一个对象都是软引用类型*/
        SoftReference<int[]>[] srArr = new SoftReference[1000];
         
        for(int i = 0; i < srArr.length; i++){
            srArr[i] = new SoftReference(new int[300000], rq);
        }
         
        /*（可能）在gc前保留下了三个强引用*/
        int[] arr1 = srArr[30].get();
        int[] arr2 = srArr[60].get();
        int[] arr3 = srArr[90].get();
         
        /*占用内存，会导致一次gc，使得只有软引用指向的对象被回收*/
        int[] strongRef = new int[200000000];
         
        Object x;
        int n = 0;
        while((x = rq.poll()) != null){
            int idx = 0;
            while(idx < srArr.length){
                if(x == srArr[idx]){
                    System.out.println("free " + x);
                    srArr[idx] = null; /*手动释放内存*/
                    n++;
                    break;
                }
                idx++;
            }
        }
         
        /*当然最简单的方法是通过isEnqueued()判断一个软引用方法是否在
         * 队列中，上面的方法只是举例
         int n = 0;
         for(int i = 0; i < srArr.length; i++){
            if(srArr[i].isEnqueued()){
                srArr[i] = null;
                n++;
            }
         }  
        */     
        System.out.println("recycle  " + n + "  SoftReference Object");
    }
}
```

一个Reference对象的生命周期如下

![image-20200707154730886](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200707154730886.png)

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

对于Cleaner类型（继承自虚引用）的对象会有额外的处理：在其指向的对象被回收时，会调用clean方法，该方法主要是用来做对应的资源回收，**在堆外内存DirectByteBuffer中就是用Cleaner进行堆外内存的回收，这也是虚引用在java中的典型应用。**



```java
public class Cleaner extends PhantomReference<Object> {
   ...
    private Cleaner(Object referent, Runnable thunk) {
        super(referent, dummyQueue);
        this.thunk = thunk;
    }
    public void clean() {
        if (remove(this)) {
            try {
                //thunk是一个Deallocator对象
                this.thunk.run();
            } catch (final Throwable var2) {
              ...
            }

        }
    }
}
```

## reference

https://juejin.im/post/5c01427ef265da6175737e14

https://www.cnblogs.com/nullzx/p/7406151.html

https://github.com/farmerjohngit/myblog/issues/10



